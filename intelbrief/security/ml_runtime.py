"""Single-process ML runtime — load the ONNX scorer once, reuse for health and runs."""

from __future__ import annotations

import gc
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentguard import AgentGuard

    from intelbrief.config import Settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_guard: AgentGuard | None = None
_guard_audit_path: str | None = None


def default_model_path() -> Path | None:
    """Return packaged risk_scorer.onnx when present."""
    try:
        import agentguard

        candidate = Path(agentguard.__file__).resolve().parent / "models" / "risk_scorer.onnx"
    except (ImportError, TypeError, OSError):
        return None
    return candidate if candidate.is_file() else None


def model_on_disk() -> bool:
    """True when the ONNX artifact exists (does not load into RAM)."""
    path = default_model_path()
    sha = path.parent / "model.sha256" if path else None
    return bool(path and sha and sha.is_file())


def ml_model_loaded() -> bool:
    """True when the shared runtime guard has an active ONNX session."""
    return _guard is not None and _guard.is_ml_model_loaded


def get_shared_guard() -> AgentGuard | None:
    return _guard


def warm_shared_guard(
    *,
    settings: Settings,
    audit_log_path: str | Path,
    manifests_dir: Path,
    task_objective: str,
    mode: str,
) -> AgentGuard:
    """Create or reuse the process-wide AgentGuard (loads ML at most once)."""
    global _guard, _guard_audit_path

    audit_str = str(audit_log_path)
    with _lock:
        if _guard is not None and _guard.is_ml_model_loaded:
            _guard_audit_path = audit_str
            logger.debug("reusing shared AgentGuard audit=%s", audit_str)
            return _guard

        from intelbrief.security.guard import build_guard
        from intelbrief.utils.model_install import ensure_model

        model_path: Path | None = None
        if settings.require_ml_model:
            model_path = ensure_model()

        _guard = build_guard(
            audit_log_path=audit_str,
            manifests_dir=manifests_dir,
            task_objective=task_objective,
            model_path=str(model_path) if model_path else None,
            require_ml_model=settings.require_ml_model,
            enable_trust_attestation=settings.enable_trust_attestation,
            mode=mode,
        )
        _guard_audit_path = audit_str
        logger.info(
            "shared AgentGuard ready ml_loaded=%s audit=%s",
            _guard.is_ml_model_loaded,
            audit_str,
        )
        return _guard


def release_shared_guard() -> None:
    """Drop the shared guard after heavy work to reclaim RAM on small instances."""
    global _guard, _guard_audit_path
    with _lock:
        if _guard is None:
            return
        logger.debug("releasing shared AgentGuard (audit=%s)", _guard_audit_path)
        _guard = None
        _guard_audit_path = None
        gc.collect()
