"""Ensure AgentGuard ONNX model is installed."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_model() -> Path:
    """Download and verify ONNX model via root install_model script."""
    root = Path(__file__).resolve().parents[2]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from install_model import ensure_model as _ensure_model

    return _ensure_model()
