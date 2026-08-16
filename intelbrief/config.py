"""Application configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """IntelBrief runtime settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "IntelBrief"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{(ROOT_DIR / 'data' / 'intelbrief.db').as_posix()}"
    )
    data_dir: Path = Field(default=ROOT_DIR / "data")
    audit_dir: Path = Field(default=ROOT_DIR / "data" / "audit")
    manifests_dir: Path = Field(default=ROOT_DIR / "manifests")
    fixtures_dir: Path = Field(default=ROOT_DIR / "intelbrief" / "static" / "fixtures")
    fixture_mode: Literal["http", "local"] = "http"

    llm_backend: Literal["ollama", "openai", "scripted"] = "ollama"
    llm_model: str = "llama3.2"
    llm_temperature: float = 0.0
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    openai_api_key: str | None = None

    agentguard_mode: Literal["monitor", "enforce"] = "enforce"
    require_ml_model: bool = True
    enable_trust_attestation: bool = True

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8501", "http://127.0.0.1:8501"])

    default_task: str = "Analyse Q3 competitor pricing from public sources"

    @field_validator("data_dir", "audit_dir", mode="after")
    @classmethod
    def ensure_dirs(cls, value: Path) -> Path:
        value.mkdir(parents=True, exist_ok=True)
        return value


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
