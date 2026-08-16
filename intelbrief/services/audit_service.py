"""Audit log parsing for API and UI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from intelbrief.schemas import AuditEntry
from intelbrief.services.layer_labels import infer_blocking_layer


def parse_audit_file(path: Path, *, limit: int = 50) -> list[AuditEntry]:
    """Read JSONL audit entries written by AgentGuard."""
    if not path.exists():
        return []
    entries: list[AuditEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        failure_reason = _pick(raw, "failure_reason", "reason")
        trust_result = _pick(raw, "trust_result")
        capability_result = _pick(raw, "capability_result")
        action = _pick(raw, "action", "decision")
        entries.append(
            AuditEntry(
                timestamp=_format_timestamp(raw.get("timestamp_ns")),
                sender_id=_pick(raw, "sender_id", "from"),
                recipient_id=_pick(raw, "recipient_id", "to"),
                action=action,
                risk_score=_float(raw.get("risk_score")),
                trust_result=trust_result,
                capability_result=capability_result,
                failure_reason=failure_reason,
                blocking_layer=infer_blocking_layer(
                    failure_reason=failure_reason,
                    trust_result=trust_result,
                    capability_result=capability_result,
                    action=action,
                ),
                raw=raw,
            )
        )
    return entries[-limit:]


def _pick(raw: dict, *keys: str) -> str | None:
    for key in keys:
        value = raw.get(key)
        if value is not None:
            return str(value)
    return None


def _float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _format_timestamp(value: object) -> str | None:
    if value is None:
        return None
    try:
        ns = int(value)
        return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return str(value)
