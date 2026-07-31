#!/usr/bin/env python3
"""Production-style multi-agent demo: unsecured vs AgentGuard-wrapped LangGraph.

Agent backends (DEMO_LLM):
  scripted  - deterministic stub (default; CI-safe)
  ollama    - local real LLM via Ollama (default model: llama3.2)
  openai    - OpenAI chat API (needs OPENAI_API_KEY)

Examples:
  py -3.12 run_prod_demo.py
  $env:DEMO_LLM='ollama'; py -3.12 run_prod_demo.py
  $env:DEMO_LLM='openai'; $env:OPENAI_API_KEY='sk-...'; py -3.12 run_prod_demo.py
"""

from __future__ import annotations

import argparse
import os
import warnings
from pathlib import Path

from agent_models import INJECTED_INSTRUCTION, build_agent_model, is_real_llm_backend
from guard_config import build_guard_kwargs
from install_model import ensure_model
from prod_pipeline import attack_succeeded, run_pipeline

ROOT = Path(__file__).resolve().parent
MANIFESTS = ROOT / "manifests"
AUDIT = ROOT / "audit_prod.jsonl"


def _ok(label: str) -> None:
    print(f"  PASS  {label}")


def _fail(label: str, detail: str) -> None:
    print(f"  FAIL  {label}: {detail}")
    raise SystemExit(1)


def _print_messages(result: dict) -> None:
    for msg in result.get("messages") or []:
        sender = msg.get("sender_id", "?")
        recipient = msg.get("recipient_id", "?")
        content = str(msg.get("content", ""))
        preview = content if len(content) <= 400 else content[:400] + "..."
        print(f"  [{sender} -> {recipient}] {preview}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AgentGuard production-style pipeline demo")
    parser.add_argument(
        "--llm",
        choices=("scripted", "ollama", "openai"),
        default=None,
        help="Agent LLM backend (sets DEMO_LLM for this run)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name (e.g. llama3.2, gpt-4o-mini); sets DEMO_LLM_MODEL",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.llm:
        os.environ["DEMO_LLM"] = args.llm
    if args.model:
        os.environ["DEMO_LLM_MODEL"] = args.model

    print("inter-agent-guard production-style agent pipeline demo\n")

    from agentguard import AgentGuard, AgentGuardException, CapabilityManifest
    from agentguard.inspector.ml_scorer import ModelNotLoadedWarning

    model = build_agent_model(poison_web=True)
    model_kind = os.environ.get("DEMO_LLM", "scripted").strip().lower()
    real = is_real_llm_backend()
    print(f"Agent model backend: {model_kind} ({type(model).__name__})")
    if hasattr(model, "model"):
        print(f"Chat model: {model.model}")
    print("Pipeline: orchestrator -> researcher -> writer (LangGraph)\n")

    # --- 1. Unsecured run ---
    print("=== 1. Unsecured pipeline (no AgentGuard) ===")
    vulnerable = run_pipeline(model=model, guard=None)
    _print_messages(vulnerable)
    print(f"  Writer action: {vulnerable.get('writer_action')!r}")
    if attack_succeeded(vulnerable):
        _ok("ATTACK SUCCEEDED without AgentGuard (prod failure mode reproduced)")
    elif real:
        print(
            "  WARN  Real LLM did not execute publish_external "
            "(models sometimes refuse). Continuing to secured run..."
        )
    else:
        _fail(
            "unsecured pipeline",
            "expected writer to follow injected publish_external instruction",
        )

    # --- 2. Secured run ---
    print("\n=== 2. Same pipeline with AgentGuard.wrap() ===")
    model_path = ensure_model()
    with warnings.catch_warnings():
        warnings.simplefilter("error", ModelNotLoadedWarning)
        # Consistency + ML + capabilities (trust off for variable real-LLM text).
        guard = AgentGuard(
            **build_guard_kwargs(
                audit_log_path=str(AUDIT),
                model_path=str(model_path),
                require_ml_model=True,
                enable_trust_attestation=not real,
            ),
        )
    if not guard.is_ml_model_loaded:
        _fail("ML model load", "risk scorer failed to load")

    for name in ("orchestrator", "researcher", "writer"):
        guard.register_agent(name, CapabilityManifest.from_yaml(str(MANIFESTS / f"{name}.yaml")))
    guard.rotate_keys()

    blocked_reason: str | None = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", ModelNotLoadedWarning)
            secured = run_pipeline(model=model, guard=guard)
        _print_messages(secured)
        print(f"  Writer action: {secured.get('writer_action')!r}")
        if attack_succeeded(secured):
            _fail(
                "secured pipeline",
                f"writer still executed injection: {secured.get('writer_action')!r}",
            )
        blocked_reason = "writer did not execute injected instruction"
    except AgentGuardException as exc:
        blocked_reason = exc.failure_reason or str(exc)
        print(f"  Interrupted at hop: {exc.sender_id} -> {exc.recipient_id}")

    if not blocked_reason:
        _fail("secured pipeline", "expected AgentGuard to block the injection")
    _ok(f"ATTACK BLOCKED by AgentGuard ({blocked_reason})")
    print(f"\nInjected instruction under test: {INJECTED_INSTRUCTION!r}")
    print(f"Audit log: {AUDIT}")
    print("\nAll production-style pipeline checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
