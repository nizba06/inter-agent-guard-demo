"""Health check routes."""

from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends

from intelbrief import __version__
from intelbrief.api.deps import get_app_settings
from intelbrief.config import Settings
from intelbrief.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_app_settings)]) -> HealthResponse:
    """Liveness and dependency probe."""
    ml_loaded = _check_ml_model(settings)
    ollama_ok = _check_ollama(settings) if settings.llm_backend == "ollama" else None
    status = "ok"
    if settings.llm_backend == "ollama" and ollama_ok is False:
        status = "degraded"
    if settings.require_ml_model and not ml_loaded:
        status = "degraded"
    return HealthResponse(
        status=status,
        app=settings.app_name,
        version=__version__,
        llm_backend=settings.llm_backend,
        llm_model=settings.llm_model,
        ml_model_loaded=ml_loaded,
        ollama_reachable=ollama_ok,
    )


def _check_ml_model(settings: Settings) -> bool:
    if not settings.require_ml_model:
        return False
    try:
        from agentguard import AgentGuard

        guard = AgentGuard(require_ml_model=False)
        return guard.is_ml_model_loaded
    except Exception:
        logger.debug("ML model health check failed", exc_info=True)
        return False


def _check_ollama(settings: Settings) -> bool:
    base = settings.ollama_base_url.rstrip("/").removesuffix("/v1")
    try:
        response = httpx.get(f"{base}/api/tags", timeout=3.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False
