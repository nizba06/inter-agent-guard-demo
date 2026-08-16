"""Tests for dynamic task objective wiring."""

from __future__ import annotations

from intelbrief.security.guard import build_task_objective


def test_build_task_objective_uses_user_brief() -> None:
    objective = build_task_objective("Track APAC SaaS pricing changes")
    assert "Track APAC SaaS pricing changes" in objective
    assert "publish_internal only" in objective


def test_build_task_objective_fallback() -> None:
    objective = build_task_objective("  ")
    assert "Q3 competitor pricing" in objective
