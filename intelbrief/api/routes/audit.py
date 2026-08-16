"""Audit log routes."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from intelbrief.api.deps import get_analysis_service, get_app_settings
from intelbrief.config import Settings
from intelbrief.schemas import AuditEntry
from intelbrief.services.analysis_service import AnalysisService
from intelbrief.services.audit_service import parse_audit_file

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/runs/{run_id}", response_model=list[AuditEntry])
def get_run_audit(
    run_id: uuid.UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> list[AuditEntry]:
    """Return AgentGuard audit entries for a secured run."""
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if not run.audit_log_path:
        return []
    return parse_audit_file(Path(run.audit_log_path))


@router.get("/recent", response_model=list[AuditEntry])
def recent_audit(
    settings: Annotated[Settings, Depends(get_app_settings)],
    limit: int = 30,
) -> list[AuditEntry]:
    """Return recent audit entries across all runs."""
    entries: list[AuditEntry] = []
    audit_dir = settings.audit_dir
    if not audit_dir.exists():
        return []
    files = sorted(audit_dir.glob("run_*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files[:10]:
        entries.extend(parse_audit_file(path, limit=limit))
    return entries[-limit:]
