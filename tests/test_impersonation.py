"""Impersonation attack scenario tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("LLM_BACKEND", "scripted")
os.environ.setdefault("REQUIRE_ML_MODEL", "false")
os.environ.setdefault("ENABLE_TRUST_ATTESTATION", "true")

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
        enable_trust_attestation=True,
        fixture_mode="local",
    )
    get_settings.cache_clear()
    monkeypatch.setattr("intelbrief.config.get_settings", lambda: settings)
    monkeypatch.setattr("intelbrief.api.deps.get_settings", lambda: settings)
    monkeypatch.setattr("intelbrief.api.deps.get_app_settings", lambda: settings)
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


def test_impersonation_secured_blocked_by_trust(client: TestClient):
    response = client.post(
        "/api/v1/runs",
        json={
            "task": "Analyse Q3 competitor pricing",
            "poisoned_source": False,
            "secured": True,
            "attack_scenario": "impersonation",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "blocked"
    assert body["attack_scenario"] == "impersonation"
    assert body.get("blocked_layer") is not None
    assert "Trust verifier" in body["blocked_layer"]
