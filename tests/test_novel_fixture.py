"""Ensure poisoned fixture avoids builtin rule signatures but keeps attack intent."""

from __future__ import annotations

from pathlib import Path

from agentguard.inspector.rule_filter import InjectionRuleFilter

from intelbrief.agents.models import INJECTED_INSTRUCTION
from intelbrief.pipeline.tools import read_fixture

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "intelbrief"
    / "static"
    / "fixtures"
    / "poisoned.html"
)


def test_poisoned_fixture_avoids_rule_filter() -> None:
    text = read_fixture(FIXTURE)
    result = InjectionRuleFilter().scan(text)
    assert not result.flagged, f"Unexpected rule matches: {result.matched_rules}"


def test_poisoned_fixture_still_contains_attack_instruction() -> None:
    text = read_fixture(FIXTURE)
    assert INJECTED_INSTRUCTION in text
