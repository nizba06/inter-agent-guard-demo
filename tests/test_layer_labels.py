"""Tests for blocking-layer inference."""

from __future__ import annotations

from intelbrief.services.layer_labels import infer_blocking_layer


def test_rule_filter_layer() -> None:
    layer = infer_blocking_layer(failure_reason="rule_filter: ignore previous instructions")
    assert layer is not None
    assert "Rule filter" in layer


def test_trust_layer() -> None:
    layer = infer_blocking_layer(failure_reason="trust: missing signature")
    assert layer is not None
    assert "Trust verifier" in layer


def test_mcp_layer() -> None:
    layer = infer_blocking_layer(failure_reason="mcp_output: ignore previous instructions")
    assert layer is not None
    assert "MCP tool output" in layer
    assert "Rule filter" in layer


def test_mcp_ml_layer() -> None:
    layer = infer_blocking_layer(failure_reason="mcp_output: risk=1.000")
    assert layer is not None
    assert "MCP tool output" in layer
    assert "ML scorer" in layer
