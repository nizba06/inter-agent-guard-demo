"""API integration tests (scripted LLM — no Ollama required)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("LLM_BACKEND", "scripted")
os.environ.setdefault("REQUIRE_ML_MODEL", "false")

from intelbrief.api.app import create_app  # noqa: E402
from intelbrief.config import Settings, get_settings  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    audit = tmp_path / "audit"
    audit.mkdir()
    settings = Settings(
        database_url=f"sqlite:///{db.as_posix()}",
        data_dir=tmp_path,
        audit_dir=audit,
        llm_backend="scripted",
        require_ml_model=False,
        fixture_mode="local",
    )
    get_settings.cache_clear()
    monkeypatch.setattr("intelbrief.config.get_settings", lambda: settings)
    monkeypatch.setattr("intelbrief.api.deps.get_settings", lambda: settings)
    monkeypatch.setattr("intelbrief.api.deps.get_app_settings", lambda: settings)
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert body["llm_backend"] == "scripted"


def test_unsecured_run_attack_succeeds(client: TestClient):
    response = client.post(
        "/api/v1/runs",
        json={
            "task": "Analyse Q3 competitor pricing",
            "poisoned_source": True,
            "secured": False,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["attack_succeeded"] is True
    assert body["security_mode"] == "unsecured"


def test_secured_run_blocks_or_completes_safely(client: TestClient):
    response = client.post(
        "/api/v1/runs",
        json={
            "task": "Analyse Q3 competitor pricing",
            "poisoned_source": True,
            "secured": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["security_mode"] == "secured"
    assert body["attack_succeeded"] is False or body["status"] == "blocked"
