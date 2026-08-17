"""IntelBrief Streamlit dashboard — calls the FastAPI backend."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
import streamlit as st

from intelbrief.security.guard import build_task_objective
from intelbrief.services.layer_labels import describe_audit_stage

API_BASE = os.environ.get("INTELBRIEF_API_URL", "http://127.0.0.1:8000/api/v1")
DEFAULT_TASK = "Analyse Q3 competitor pricing from public sources"

TASK_PRESETS: dict[str, str] = {
    "Q3 competitor pricing (recommended demo)": DEFAULT_TASK,
    "EU cloud vendor contract renewals": "Analyse EU cloud vendor contract renewal terms from public filings",
    "Supply chain risk for semiconductor inputs": "Summarise supply chain risks for semiconductor inputs from public news",
    "Custom brief (type below)": "",
}


@st.cache_resource
def _api_client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE, timeout=600.0)


@st.cache_data(ttl=30, show_spinner=False)
def _get_health() -> dict[str, Any]:
    response = _api_client().get("/health")
    response.raise_for_status()
    return response.json()


def _wait_for_health(*, attempts: int = 30, delay_seconds: float = 2.0) -> dict[str, Any]:
    """Retry health while the API finishes cold start (Render free tier can be slow)."""
    last_exc: Exception | None = None
    for _ in range(attempts):
        try:
            return _get_health()
        except httpx.HTTPError as exc:
            last_exc = exc
            time.sleep(delay_seconds)
    assert last_exc is not None
    raise last_exc


@st.cache_data(ttl=5, show_spinner=False)
def _list_runs() -> list[dict[str, Any]]:
    response = _api_client().get("/runs")
    response.raise_for_status()
    return response.json()


@st.cache_data(show_spinner=False)
def _get_run(run_id: str) -> dict[str, Any]:
    response = _api_client().get(f"/runs/{run_id}")
    response.raise_for_status()
    return response.json()


@st.cache_data(show_spinner=False)
def _get_audit(run_id: str) -> list[dict[str, Any]]:
    response = _api_client().get(f"/audit/runs/{run_id}")
    response.raise_for_status()
    return response.json()


def _invalidate_run_caches() -> None:
    _list_runs.clear()
    _get_run.clear()
    _get_audit.clear()


def _create_run(payload: dict[str, Any]) -> dict[str, Any]:
    response = _api_client().post("/runs", json=payload)
    response.raise_for_status()
    result = response.json()
    _invalidate_run_caches()
    return result


def _status_badge(status: str, attack: bool, *, secured: bool = False) -> str:
    if status == "blocked":
        return "🛡️ Blocked by AgentGuard"
    if status == "failed" and secured and attack:
        return "⚠️ Guard failed — attack succeeded"
    if status == "failed":
        return "❌ Run failed"
    if attack:
        return "⚠️ Attack succeeded"
    return "✅ Completed safely"


def _run_label(run: dict[str, Any]) -> str:
    return (
        f"{run['security_mode']} · {run.get('attack_scenario', 'injection')} · "
        f"{run['status']} · {run['task'][:35]} ({run['id'][:8]})"
    )


def _select_run(run_id: str) -> None:
    st.session_state["selected_run"] = run_id


def _render_run_detail(run_id: str) -> None:
    detail = _get_run(run_id)
    secured = detail.get("security_mode") == "secured"
    st.subheader(
        _status_badge(detail["status"], detail["attack_succeeded"], secured=secured)
    )
    st.caption(f"Run `{detail['id']}` · {detail['security_mode']} · {detail['llm_backend']}/{detail['llm_model']}")
    if detail.get("blocked_layer"):
        st.success(f"**Blocked at:** {detail['blocked_layer']}")
    if detail.get("blocked_hop"):
        st.caption(f"**Stage:** {detail['blocked_hop']}")
    if detail.get("blocked_reason"):
        st.caption(f"**Reason:** `{detail['blocked_reason']}`")
    st.json(
        {
            "attack_scenario": detail.get("attack_scenario"),
            "writer_action": detail.get("writer_action"),
            "blocked_reason": detail.get("blocked_reason"),
            "blocked_layer": detail.get("blocked_layer"),
            "blocked_hop": detail.get("blocked_hop"),
            "attack_succeeded": detail.get("attack_succeeded"),
            "error": detail.get("error"),
        }
    )
    st.markdown("**Message trace**")
    messages = detail.get("messages") or []
    if not messages:
        st.info("No inter-agent messages recorded for this run.")
    for msg in messages:
        with st.expander(f"{msg['sender_id']} → {msg['recipient_id']}"):
            st.write(msg["content"])
    if detail.get("error"):
        st.error(detail["error"])


def _render_audit(run_id: str) -> None:
    entries = _get_audit(run_id)
    if not entries:
        st.info("No audit entries (unsecured runs do not write audit logs).")
        return

    st.caption(
        "Read `failure_reason` for the exact layer. "
        "`tool:…` sender = blocked at fetch; agent names = inter-agent hop."
    )
    blocking = next(
        (e for e in entries if e.get("action") in ("QUARANTINE", "BLOCK")),
        None,
    )
    if blocking:
        stage = describe_audit_stage(blocking.get("sender_id"), blocking.get("recipient_id"))
        st.error(
            f"**Attack blocked** at {blocking.get('blocking_layer') or blocking.get('failure_reason')} "
            f"· {stage}"
        )

    for entry in entries:
        is_block = entry.get("action") in ("QUARANTINE", "BLOCK")
        stage = describe_audit_stage(entry.get("sender_id"), entry.get("recipient_id"))
        header = f"{'⛔ ' if is_block else ''}{stage} · {entry.get('action')}"
        with st.expander(header, expanded=is_block):
            layer = entry.get("blocking_layer")
            if layer:
                st.markdown(f"**Blocking layer:** {layer}")
            if entry.get("failure_reason"):
                st.markdown(f"**Failure reason:** `{entry['failure_reason']}`")
            cols = st.columns(4)
            cols[0].write(entry.get("action"))
            cols[1].write(entry.get("trust_result"))
            cols[2].write(entry.get("capability_result"))
            cols[3].write(f"risk={entry.get('risk_score')}")
            st.json(entry)


@st.fragment
def _render_sidebar() -> None:
    st.header("New analysis")
    preset = st.selectbox(
        "Brief preset",
        list(TASK_PRESETS.keys()),
        index=0,
        help="Use the recommended preset for live demos. Custom briefs work but may vary with real LLMs.",
    )
    if preset == "Custom brief (type below)":
        task = st.text_area("Brief", value=DEFAULT_TASK, height=100, key="custom_brief")
    else:
        task = TASK_PRESETS[preset]
        st.text_area("Brief", value=task, height=100, disabled=True)
    st.caption("AgentGuard objective (secured runs): " + build_task_objective(task))
    poisoned = st.checkbox("Simulate compromised web source", value=True)
    secured_mode = st.selectbox("AgentGuard mode", ["enforce", "monitor"], index=0)
    st.info(
        "**Injection demo:** Compare both (poisoned web content). "
        "**Impersonation demo:** unsigned message claiming to be orchestrator — "
        "blocked by Trust verifier when secured. Trust attestation is **on** for all secured runs."
    )
    st.divider()
    st.markdown("**Injection attack**")
    if st.button("Compare both (injection demo)", use_container_width=True, type="primary"):
        _run_and_store(task, poisoned, secured=False, label="unsecured", attack_scenario="injection")
        _run_and_store(
            task,
            poisoned,
            secured=True,
            agentguard_mode=secured_mode,
            label="secured",
            attack_scenario="injection",
        )
        st.rerun()
    st.markdown("**Impersonation attack**")
    if st.button("Impersonation — WITHOUT AgentGuard", use_container_width=True):
        _run_and_store(
            task,
            poisoned=False,
            secured=False,
            label="impersonation unsecured",
            attack_scenario="impersonation",
        )
        st.rerun()
    if st.button("Impersonation — WITH AgentGuard", use_container_width=True):
        _run_and_store(
            task,
            poisoned=False,
            secured=True,
            agentguard_mode=secured_mode,
            label="impersonation secured",
            attack_scenario="impersonation",
        )
        st.rerun()
    st.divider()
    if st.button("Run WITHOUT AgentGuard", use_container_width=True, type="secondary"):
        _run_and_store(task, poisoned, secured=False, attack_scenario="injection")
        st.rerun()
    if st.button("Run WITH AgentGuard", use_container_width=True):
        _run_and_store(
            task,
            poisoned,
            secured=True,
            agentguard_mode=secured_mode,
            attack_scenario="injection",
        )
        st.rerun()
    st.divider()
    st.caption("Use AgentGuard in your project:")
    st.code("pip install inter-agent-guard", language="bash")
    st.markdown(
        "[PyPI](https://pypi.org/project/inter-agent-guard/) · "
        "[Docs](https://inter-agent-guard.readthedocs.io/) · "
        "[GitHub](https://github.com/nizba06/agentguard)"
    )


@st.fragment
def _render_run_explorer() -> None:
    runs = _list_runs()
    if not runs:
        st.info("No runs yet. Use the sidebar to start an analysis.")
        return

    run_ids = [r["id"] for r in runs]
    run_by_id = {r["id"]: r for r in runs}

    if st.session_state.get("selected_run") not in run_by_id:
        st.session_state["selected_run"] = run_ids[0]

    selected = st.selectbox(
        "Selected run",
        run_ids,
        format_func=lambda rid: _run_label(run_by_id[rid]),
        key="selected_run",
    )

    view = st.radio(
        "View",
        ["Run history", "Run detail", "Audit log"],
        horizontal=True,
        key="run_view",
    )

    if view == "Run history":
        header = st.columns([3, 1, 1, 2, 2, 1])
        header[0].markdown("**Task**")
        header[1].markdown("**Scenario**")
        header[2].markdown("**Mode**")
        header[3].markdown("**Outcome**")
        header[4].markdown("**Blocked layer**")
        header[5].markdown("**View**")
        for run in runs:
            cols = st.columns([3, 1, 1, 2, 2, 1])
            is_selected = selected == run["id"]
            cols[0].write(("▶ " if is_selected else "") + run["task"][:60])
            cols[1].write(run.get("attack_scenario", "injection"))
            cols[2].write(run["security_mode"])
            cols[3].write(
                _status_badge(
                    run["status"],
                    run["attack_succeeded"],
                    secured=run["security_mode"] == "secured",
                )
            )
            cols[4].write(run.get("blocked_layer") or "—")
            cols[5].button(
                "View",
                key=f"view-{run['id']}",
                on_click=_select_run,
                args=(run["id"],),
                type="primary" if is_selected else "secondary",
            )
    elif view == "Run detail":
        _render_run_detail(selected)
    else:
        _render_audit(selected)


def main() -> None:
    st.set_page_config(page_title="IntelBrief", page_icon="🛡️", layout="wide")
    st.title("IntelBrief")
    st.caption("Competitive intelligence pipeline secured by AgentGuard")

    if "selected_run" not in st.session_state:
        st.session_state["selected_run"] = None

    try:
        with st.spinner("Connecting to API (cold start may take up to 1 minute)…"):
            health = _wait_for_health()
    except httpx.HTTPError as exc:
        st.error(f"API unreachable at {API_BASE}. The service may be restarting — refresh in a minute.")
        st.code(str(exc))
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("API", health.get("status", "?"))
    col2.metric("LLM", f"{health.get('llm_backend')}/{health.get('llm_model')}")
    col3.metric("ML model", "loaded" if health.get("ml_model_loaded") else "missing")
    ollama = health.get("ollama_reachable")
    col4.metric("Ollama", "up" if ollama else ("n/a" if ollama is None else "down"))

    with st.sidebar:
        _render_sidebar()

    _render_run_explorer()


def _run_and_store(
    task: str,
    poisoned: bool,
    *,
    secured: bool,
    agentguard_mode: str | None = None,
    attack_scenario: str = "injection",
    label: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "task": task,
        "poisoned_source": poisoned,
        "secured": secured,
        "attack_scenario": attack_scenario,
    }
    if agentguard_mode:
        payload["agentguard_mode"] = agentguard_mode
    with st.spinner(
        f"Running {attack_scenario} / {'secured' if secured else 'unsecured'} pipeline…"
    ):
        try:
            result = _create_run(payload)
        except httpx.HTTPError as exc:
            st.error(f"Run failed: {exc}")
            return
    st.session_state["selected_run"] = result["id"]
    layer = result.get("blocked_layer")
    layer_text = f" layer={layer}" if layer else ""
    st.success(
        f"{label or ('secured' if secured else 'unsecured')} run finished: "
        f"{result['status']} — writer={result.get('writer_action')!r}{layer_text}"
    )


if __name__ == "__main__":
    main()
