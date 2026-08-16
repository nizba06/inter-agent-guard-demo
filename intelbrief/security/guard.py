"""AgentGuard factory and task objective configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentguard import AgentGuard, CapabilityManifest

DEFAULT_TASK_OBJECTIVE_SUFFIX = (
    "Delegate sub-tasks, share research summaries, and draft internal reports "
    "using publish_internal only."
)

# Fallback when no user brief is supplied.
DEFAULT_TASK_OBJECTIVE = (
    "Multi-agent pipeline: analyse Q3 competitor pricing, "
    + DEFAULT_TASK_OBJECTIVE_SUFFIX
)

CONSISTENCY_THRESHOLD = 0.45
CONSISTENCY_ML_RISK_FLOOR = 0.0


def build_task_objective(user_task: str) -> str:
    """Derive AgentGuard consistency objective from the UI/API brief."""
    brief = user_task.strip()
    if not brief:
        return DEFAULT_TASK_OBJECTIVE
    return f"Multi-agent pipeline: {brief}. {DEFAULT_TASK_OBJECTIVE_SUFFIX}"


def build_guard(
    *,
    audit_log_path: str | Path,
    manifests_dir: Path,
    task_objective: str | None = None,
    model_path: str | Path | None = None,
    require_ml_model: bool = True,
    enable_trust_attestation: bool = True,
    mode: str = "enforce",
) -> AgentGuard:
    """Create a fully configured AgentGuard instance for IntelBrief."""
    kwargs: dict[str, Any] = {
        "audit_log_path": str(audit_log_path),
        "task_objective": task_objective or DEFAULT_TASK_OBJECTIVE,
        "enable_consistency_check": True,
        "consistency_threshold": CONSISTENCY_THRESHOLD,
        "consistency_ml_risk_floor": CONSISTENCY_ML_RISK_FLOOR,
        "enable_trust_attestation": enable_trust_attestation,
        "require_ml_model": require_ml_model,
        "mode": mode,
    }
    if model_path is not None:
        kwargs["model_path"] = str(model_path)

    guard = AgentGuard(**kwargs)
    for role in ("orchestrator", "researcher", "writer"):
        manifest_path = manifests_dir / f"{role}.yaml"
        guard.register_agent(role, CapabilityManifest.from_yaml(str(manifest_path)))
    guard.rotate_keys()
    return guard
