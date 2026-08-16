"""Business logic for analysis runs."""

from __future__ import annotations

import logging
import uuid

from intelbrief.agents.models import build_agent_model
from intelbrief.config import Settings, get_settings
from intelbrief.pipeline.runner import AnalysisRunner
from intelbrief.schemas import CreateRunRequest, RunResponse, RunStatus, RunSummary
from intelbrief.storage.run_repository import RunRepository, to_summary

logger = logging.getLogger(__name__)


class AnalysisService:
    """Coordinates pipeline execution and persistence."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._repo = RunRepository(self._settings.database_url)
        self._runner = AnalysisRunner(self._settings)

    def create_run(self, request: CreateRunRequest) -> RunResponse:
        run_id = uuid.uuid4()
        model = build_agent_model(self._settings, poison_web=request.poisoned_source)
        self._repo.insert_pending(
            run_id,
            task=request.task,
            poisoned_source=request.poisoned_source,
            secured=request.secured,
            llm_backend=self._settings.llm_backend,
            llm_model=model.model_name,
        )

        fixture_base = (
            "local:"
            if self._settings.fixture_mode == "local"
            else f"http://127.0.0.1:{self._settings.api_port}/fixtures"
        )
        result = self._runner.execute(
            run_id=run_id,
            task=request.task,
            poisoned_source=request.poisoned_source,
            secured=request.secured,
            attack_scenario=request.attack_scenario.value,
            agentguard_mode=request.agentguard_mode,
            fixture_base_url=fixture_base,
        )

        self._repo.finalize(
            run_id,
            status=result.status,
            writer_action=result.writer_action,
            attack_succeeded=result.attack_succeeded,
            blocked_reason=result.blocked_reason,
            blocked_hop=result.blocked_hop,
            blocked_layer=result.blocked_layer,
            attack_scenario=result.attack_scenario,
            messages=result.messages,
            audit_log_path=result.audit_log_path,
            agentguard_mode=result.agentguard_mode,
            error=result.error,
        )

        record = self._repo.get(run_id)
        if record is None:
            msg = f"Run {run_id} missing after finalize"
            raise RuntimeError(msg)
        return _to_response(record)

    def get_run(self, run_id: uuid.UUID) -> RunResponse | None:
        record = self._repo.get(run_id)
        if record is None:
            return None
        return _to_response(record)

    def list_runs(self, limit: int = 20) -> list[RunSummary]:
        return [to_summary(record) for record in self._repo.list_recent(limit)]


def _to_response(record: dict) -> RunResponse:
    return RunResponse(
        id=record["id"],
        status=record["status"],
        security_mode=record["security_mode"],
        task=record["task"],
        poisoned_source=record["poisoned_source"],
        writer_action=record["writer_action"],
        attack_succeeded=record["attack_succeeded"],
        blocked_reason=record["blocked_reason"],
        blocked_hop=record["blocked_hop"],
        blocked_layer=record.get("blocked_layer"),
        attack_scenario=record.get("attack_scenario", "injection"),
        messages=record["messages"],
        audit_log_path=record["audit_log_path"],
        llm_backend=record["llm_backend"],
        llm_model=record["llm_model"],
        agentguard_mode=record["agentguard_mode"],
        created_at=record["created_at"],
        completed_at=record["completed_at"],
        error=record["error"],
    )
