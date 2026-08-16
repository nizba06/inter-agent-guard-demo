"""Analysis run routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from intelbrief.api.deps import get_analysis_service
from intelbrief.schemas import CreateRunRequest, RunResponse, RunSummary
from intelbrief.services.analysis_service import AnalysisService

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    request: CreateRunRequest,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> RunResponse:
    """Execute a multi-agent analysis pipeline."""
    return service.create_run(request)


@router.get("", response_model=list[RunSummary])
def list_runs(
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
    limit: int = 20,
) -> list[RunSummary]:
    """List recent pipeline runs."""
    return service.list_runs(limit=min(limit, 100))


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: uuid.UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> RunResponse:
    """Fetch a single run by id."""
    result = service.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return result
