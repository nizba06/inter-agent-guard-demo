"""Recommended AgentGuard settings for production-style demos.

Defense in depth:
  - Rules + ML (when ONNX is installed) for known / training-like injections
  - Consistency check for semantic drift / novel paraphrases
  - Capability manifests to block forbidden tools even if a message slips through
"""

from __future__ import annotations

# Declare the intended pipeline goal — consistency compares each message to this.
TASK_OBJECTIVE = (
    "Multi-agent pipeline: analyse Q3 competitor pricing, delegate sub-tasks, "
    "share research summaries, and draft internal reports using publish_internal only."
)

# Catch novel paraphrases even when ML risk ~ 0 (see test_novel_messages.py).
# 0.45 balances far-paraphrase catch vs benign handoffs for TASK_OBJECTIVE above.
CONSISTENCY_THRESHOLD = 0.45
CONSISTENCY_ML_RISK_FLOOR = 0.0


def build_guard_kwargs(
    *,
    audit_log_path: str,
    model_path: str | None = None,
    require_ml_model: bool = True,
    enable_trust_attestation: bool = False,
) -> dict:
    """Return kwargs for AgentGuard with recommended demo/production tuning."""
    kwargs: dict = {
        "audit_log_path": audit_log_path,
        "task_objective": TASK_OBJECTIVE,
        "enable_consistency_check": True,
        "consistency_threshold": CONSISTENCY_THRESHOLD,
        "consistency_ml_risk_floor": CONSISTENCY_ML_RISK_FLOOR,
        "enable_trust_attestation": enable_trust_attestation,
        "require_ml_model": require_ml_model,
    }
    if model_path is not None:
        kwargs["model_path"] = model_path
    return kwargs
