"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from intelbrief import __version__
from intelbrief.api.deps import get_app_settings
from intelbrief.api.routes import audit, health, runs
from intelbrief.config import Settings
from intelbrief.logging_setup import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    configure_logging(settings.log_level)
    logger.info(
        "startup app=%s env=%s llm=%s/%s",
        settings.app_name,
        settings.environment,
        settings.llm_backend,
        settings.llm_model,
    )
    if settings.require_ml_model:
        try:
            from intelbrief.security.ml_runtime import model_on_disk

            if not model_on_disk():
                from intelbrief.utils.model_install import ensure_model

                ensure_model()
            logger.info("ml_model_on_disk=%s", model_on_disk())
        except Exception:
            logger.warning("ml_model_missing — secured runs will fail until install_model.py succeeds")
    yield
    logger.info("shutdown app=%s", settings.app_name)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the IntelBrief API application."""
    cfg = settings or get_app_settings()
    app = FastAPI(
        title=cfg.app_name,
        version=__version__,
        description="Competitive intelligence multi-agent pipeline secured by AgentGuard.",
        lifespan=lifespan,
    )
    app.state.settings = cfg

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = cfg.api_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(runs.router, prefix=prefix)
    app.include_router(audit.router, prefix=prefix)

    fixtures_path = cfg.fixtures_dir
    fixtures_path.mkdir(parents=True, exist_ok=True)
    app.mount("/fixtures", StaticFiles(directory=str(fixtures_path)), name="fixtures")

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "app": cfg.app_name,
            "version": __version__,
            "docs": "/docs",
            "health": f"{prefix}/health",
        }

    return app


app = create_app()
