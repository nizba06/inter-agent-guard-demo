"""FastAPI dependencies."""

from __future__ import annotations

from intelbrief.config import Settings, get_settings
from intelbrief.services.analysis_service import AnalysisService


def get_analysis_service() -> AnalysisService:
    return AnalysisService(get_settings())


def get_app_settings() -> Settings:
    return get_settings()
