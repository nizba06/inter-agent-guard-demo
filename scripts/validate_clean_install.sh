#!/usr/bin/env bash
# Validate a clean install on Linux/macOS (CI-friendly).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Clean install validation (IntelBrief)"
PY="${PYTHON:-python3.12}"

echo "==> Install package + dev deps"
"$PY" -m pip install -e ".[dev]" -q

echo "==> Run tests (scripted LLM, no Ollama)"
export LLM_BACKEND=scripted
export REQUIRE_ML_MODEL=false
export FIXTURE_MODE=local
"$PY" -m pytest tests/ -q

echo "==> Smoke: health endpoint"
"$PY" - <<'PY'
import os
os.environ.setdefault("LLM_BACKEND", "scripted")
os.environ.setdefault("REQUIRE_ML_MODEL", "false")
os.environ.setdefault("FIXTURE_MODE", "local")
from fastapi.testclient import TestClient
from intelbrief.api.app import create_app
from intelbrief.config import Settings, get_settings
from pathlib import Path
import tempfile

tmp = Path(tempfile.mkdtemp())
s = Settings(
    database_url=f"sqlite:///{(tmp / 't.db').as_posix()}",
    data_dir=tmp,
    audit_dir=tmp / "audit",
    llm_backend="scripted",
    require_ml_model=False,
    fixture_mode="local",
)
get_settings.cache_clear()
app = create_app(s)
with TestClient(app) as c:
    r = c.get("/api/v1/health")
    assert r.status_code == 200, r.text
    assert r.json()["llm_backend"] == "scripted"
print("health OK")
PY

echo ""
echo "PASS: clean install validation complete"
