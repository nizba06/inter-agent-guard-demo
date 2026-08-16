"""Pydantic models for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Pipeline run lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class SecurityMode(str, Enum):
    """Whether AgentGuard protects the run."""

    UNSECURED = "unsecured"
    SECURED = "secured"


class AttackScenario(str, Enum):
    """Which attack story the pipeline demonstrates."""

    INJECTION = "injection"
    IMPERSONATION = "impersonation"


class CreateRunRequest(BaseModel):
    """Start a new analysis pipeline."""

    task: str = Field(min_length=3, max_length=2000)
    poisoned_source: bool = Field(
        default=True,
        description="When true, researcher fetches a compromised fixture page.",
    )
    secured: bool = Field(
        default=True,
        description="When true, wrap the pipeline with AgentGuard.",
    )
    attack_scenario: AttackScenario = Field(
        default=AttackScenario.INJECTION,
        description="injection = poisoned web content; impersonation = unsigned sender",
    )
    agentguard_mode: str | None = Field(
        default=None,
        description="Override global AgentGuard mode: monitor or enforce.",
    )


class AgentMessage(BaseModel):
    """Single inter-agent message in the pipeline trace."""

    sender_id: str
    recipient_id: str
    content: str


class RunResponse(BaseModel):
    """Full result of a pipeline run."""

    id: UUID
    status: RunStatus
    security_mode: SecurityMode
    task: str
    poisoned_source: bool
    writer_action: str | None = None
    attack_succeeded: bool = False
    blocked_reason: str | None = None
    blocked_hop: str | None = None
    blocked_layer: str | None = None
    attack_scenario: str = "injection"
    messages: list[AgentMessage] = Field(default_factory=list)
    audit_log_path: str | None = None
    llm_backend: str
    llm_model: str
    agentguard_mode: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class RunSummary(BaseModel):
    """Lightweight run listing entry."""

    id: UUID
    status: RunStatus
    security_mode: SecurityMode
    task: str
    attack_succeeded: bool
    blocked_reason: str | None = None
    blocked_layer: str | None = None
    attack_scenario: str = "injection"
    created_at: datetime


class AuditEntry(BaseModel):
    """Parsed audit log entry for the UI."""

    timestamp: str | None = None
    sender_id: str | None = None
    recipient_id: str | None = None
    action: str | None = None
    risk_score: float | None = None
    trust_result: str | None = None
    capability_result: str | None = None
    failure_reason: str | None = None
    blocking_layer: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Service health probe."""

    status: str
    app: str
    version: str
    llm_backend: str
    llm_model: str
    ml_model_loaded: bool
    ollama_reachable: bool | None = None
