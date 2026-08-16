# Validate a clean install on Windows (PowerShell).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==> Clean install validation (IntelBrief)"
$Py = if ($env:PYTHON) { $env:PYTHON } else { "py" }
$PyArgs = if ($Py -eq "py") { @("-3.12") } else { @() }

Write-Host "==> Install package + dev deps"
& $Py @PyArgs -m pip install -e ".[dev]" -q

Write-Host "==> Run tests (scripted LLM, no Ollama)"
$env:LLM_BACKEND = "scripted"
$env:REQUIRE_ML_MODEL = "false"
$env:FIXTURE_MODE = "local"
& $Py @PyArgs -m pytest tests/ -q

Write-Host "==> Smoke: health endpoint"
& $Py @PyArgs -c @"
import os
os.environ.setdefault('LLM_BACKEND', 'scripted')
os.environ.setdefault('REQUIRE_ML_MODEL', 'false')
os.environ.setdefault('FIXTURE_MODE', 'local')
from fastapi.testclient import TestClient
from intelbrief.api.app import create_app
from intelbrief.config import Settings, get_settings
from pathlib import Path
import tempfile

tmp = Path(tempfile.mkdtemp())
s = Settings(
    database_url=f'sqlite:///{(tmp / \"t.db\").as_posix()}',
    data_dir=tmp,
    audit_dir=tmp / 'audit',
    llm_backend='scripted',
    require_ml_model=False,
    fixture_mode='local',
)
get_settings.cache_clear()
app = create_app(s)
with TestClient(app) as c:
    r = c.get('/api/v1/health')
    assert r.status_code == 200, r.text
    assert r.json()['llm_backend'] == 'scripted'
print('health OK')
"@

Write-Host ""
Write-Host "PASS: clean install validation complete"
