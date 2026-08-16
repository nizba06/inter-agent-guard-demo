"""Map AgentGuard audit fields to human-readable blocking layers."""

from __future__ import annotations

LAYER_LABELS: dict[str, str] = {
    "rule_filter": "Layer 1 — Rule filter (Aho-Corasick)",
    "ml_scorer": "Layer 2 — ML scorer (DeBERTa ONNX)",
    "consistency": "Layer 3 — Consistency check (embeddings)",
    "trust": "Layer 4 — Trust verifier (Ed25519)",
    "capability": "Layer 5 — Capability enforcer (YAML manifest)",
    "mcp_output": "MCP tool output inspector",
    "message_size": "Message size limit",
}


def infer_blocking_layer(
    *,
    failure_reason: str | None = None,
    trust_result: str | None = None,
    capability_result: str | None = None,
    action: str | None = None,
) -> str | None:
    """Derive which AgentGuard layer blocked or flagged a message."""
    if failure_reason:
        reason = failure_reason.lower()
        if reason.startswith("rule_filter:"):
            return LAYER_LABELS["rule_filter"]
        if reason.startswith("ml_scorer:"):
            return LAYER_LABELS["ml_scorer"]
        if reason.startswith("consistency:"):
            return LAYER_LABELS["consistency"]
        if reason.startswith("trust:"):
            return LAYER_LABELS["trust"]
        if reason.startswith("mcp_output:"):
            detail = failure_reason.split(":", 1)[1].strip()
            if detail.startswith("risk="):
                return f"MCP tool output — {LAYER_LABELS['ml_scorer']}"
            return f"MCP tool output — {LAYER_LABELS['rule_filter']}"
        if reason.startswith("message_size:"):
            return LAYER_LABELS["message_size"]
        if "capability" in reason:
            return LAYER_LABELS["capability"]

    if action in ("BLOCK", "QUARANTINE"):
        if trust_result and trust_result not in (None, "PASS", "SKIP", "pass", "skip"):
            return LAYER_LABELS["trust"]
        if capability_result and capability_result not in (None, "PASS", "SKIP", "pass", "skip"):
            return LAYER_LABELS["capability"]

    return None


def describe_audit_stage(sender_id: str | None, recipient_id: str | None) -> str:
    """Human-readable pipeline stage for an audit entry."""
    sender = sender_id or "?"
    recipient = recipient_id or "?"
    if sender.startswith("tool:"):
        tool = sender.removeprefix("tool:")
        return f"Tool fetch ({tool}) → {recipient}"
    return f"Inter-agent hop: {sender} → {recipient}"
