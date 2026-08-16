"""Execute IntelBrief analysis runs."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentguard.exceptions import AgentGuardException
from agentguard.inspector.ml_scorer import ModelNotLoadedWarning
from agentguard.mcp.output_inspector import MCPPoisoningException

from intelbrief.agents.models import AgentModel, build_agent_model
from intelbrief.config import Settings, get_settings
from intelbrief.pipeline.graph import PipelineContext, attack_succeeded, build_graph
from intelbrief.pipeline.tools import build_fetch_tool
from intelbrief.schemas import AgentMessage, RunStatus, SecurityMode
from intelbrief.security.guard import build_task_objective
from intelbrief.security.ml_runtime import warm_shared_guard
from intelbrief.services.layer_labels import infer_blocking_layer

logger = logging.getLogger(__name__)


@dataclass
class PipelineRunResult:
    """In-memory pipeline outcome before persistence."""

    run_id: uuid.UUID
    status: RunStatus
    security_mode: SecurityMode
    task: str
    poisoned_source: bool
    writer_action: str | None
    attack_succeeded: bool
    blocked_reason: str | None
    blocked_hop: str | None
    blocked_layer: str | None
    attack_scenario: str
    messages: list[AgentMessage]
    audit_log_path: str | None
    llm_backend: str
    llm_model: str
    agentguard_mode: str | None
    error: str | None = None


class AnalysisRunner:
    """Runs secured or unsecured multi-agent pipelines."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def execute(
        self,
        *,
        run_id: uuid.UUID,
        task: str,
        poisoned_source: bool,
        secured: bool,
        attack_scenario: str = "injection",
        agentguard_mode: str | None = None,
        fixture_base_url: str | None = None,
    ) -> PipelineRunResult:
        settings = self._settings
        model = build_agent_model(settings, poison_web=poisoned_source)
        guard: Any | None = None
        audit_path: Path | None = None
        mode = agentguard_mode or settings.agentguard_mode

        if secured:
            audit_path = settings.audit_dir / f"run_{run_id}.jsonl"
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ModelNotLoadedWarning)
                guard = warm_shared_guard(
                    settings=settings,
                    audit_log_path=audit_path,
                    manifests_dir=settings.manifests_dir,
                    task_objective=build_task_objective(task),
                    mode=mode,
                )
            if settings.require_ml_model and not guard.is_ml_model_loaded:
                return PipelineRunResult(
                    run_id=run_id,
                    status=RunStatus.FAILED,
                    security_mode=SecurityMode.SECURED,
                    task=task,
                    poisoned_source=poisoned_source,
                    writer_action=None,
                    attack_succeeded=False,
                    blocked_reason=None,
                    blocked_hop=None,
                    blocked_layer=None,
                    attack_scenario=attack_scenario,
                    messages=[],
                    audit_log_path=str(audit_path) if audit_path else None,
                    llm_backend=settings.llm_backend,
                    llm_model=model.model_name,
                    agentguard_mode=mode,
                    error="AgentGuard ML model failed to load. Run install_model.py first.",
                )

        fetch_tool = build_fetch_tool(guard)
        ctx = PipelineContext(model=model, guard=guard, fetch_tool=fetch_tool)
        graph = build_graph(ctx, attack_scenario=attack_scenario)  # type: ignore[arg-type]
        base = fixture_base_url or f"http://127.0.0.1:{settings.api_port}/fixtures"

        initial_state = {
            "task": task,
            "poisoned_source": poisoned_source,
            "fixture_base_url": base,
            "attack_scenario": attack_scenario,
            "messages": [],
            "writer_action": "",
        }

        security_mode = SecurityMode.SECURED if secured else SecurityMode.UNSECURED
        blocked_reason: str | None = None
        blocked_hop: str | None = None
        blocked_layer: str | None = None
        writer_action: str | None = None
        messages: list[AgentMessage] = []
        status = RunStatus.COMPLETED

        try:
            logger.info(
                "pipeline_start run_id=%s secured=%s poisoned=%s backend=%s",
                run_id,
                secured,
                poisoned_source,
                settings.llm_backend,
            )
            result = graph.invoke(initial_state)
            writer_action = str(result.get("writer_action", ""))
            for msg in result.get("messages") or []:
                messages.append(
                    AgentMessage(
                        sender_id=str(msg.get("sender_id", "?")),
                        recipient_id=str(msg.get("recipient_id", "?")),
                        content=str(msg.get("content", "")),
                    )
                )
            succeeded = attack_succeeded(result)
            if secured and succeeded:
                status = RunStatus.FAILED
            elif not secured and succeeded:
                status = RunStatus.COMPLETED
            elif secured and not succeeded:
                status = RunStatus.COMPLETED
            else:
                status = RunStatus.COMPLETED
        except (AgentGuardException, MCPPoisoningException) as exc:
            status = RunStatus.BLOCKED
            blocked_reason = getattr(exc, "failure_reason", None) or str(exc)
            blocked_layer = infer_blocking_layer(failure_reason=blocked_reason)
            blocked_hop = getattr(exc, "sender_id", None)
            if hasattr(exc, "recipient_id") and blocked_hop:
                blocked_hop = f"{exc.sender_id} -> {exc.recipient_id}"  # type: ignore[union-attr]
            elif blocked_hop is None:
                blocked_hop = "fetch_url (MCP tool output)"
            logger.warning(
                "pipeline_blocked run_id=%s reason=%s hop=%s",
                run_id,
                blocked_reason,
                blocked_hop,
            )
        except Exception as exc:  # noqa: BLE001 — surface pipeline failures to API
            logger.exception("pipeline_failed run_id=%s", run_id)
            return PipelineRunResult(
                run_id=run_id,
                status=RunStatus.FAILED,
                security_mode=security_mode,
                task=task,
                poisoned_source=poisoned_source,
                writer_action=writer_action,
                attack_succeeded=False,
                blocked_reason=blocked_reason,
                blocked_hop=blocked_hop,
                blocked_layer=blocked_layer,
                attack_scenario=attack_scenario,
                messages=messages,
                audit_log_path=str(audit_path) if audit_path else None,
                llm_backend=settings.llm_backend,
                llm_model=model.model_name,
                agentguard_mode=mode if secured else None,
                error=str(exc),
            )

        succeeded = attack_succeeded({"writer_action": writer_action or ""})
        return PipelineRunResult(
            run_id=run_id,
            status=status,
            security_mode=security_mode,
            task=task,
            poisoned_source=poisoned_source,
            writer_action=writer_action,
            attack_succeeded=succeeded,
            blocked_reason=blocked_reason,
            blocked_hop=blocked_hop,
            blocked_layer=blocked_layer,
            attack_scenario=attack_scenario,
            messages=messages,
            audit_log_path=str(audit_path) if audit_path else None,
            llm_backend=settings.llm_backend,
            llm_model=model.model_name,
            agentguard_mode=mode if secured else None,
        )
