#!/usr/bin/env python3
"""Download risk_scorer.onnx from the AgentGuard GitHub release into the installed package.

The ONNX weights are not in the PyPI wheel (~540 MB). They ship on the public
nizba06/agentguard v0.1.0 GitHub release. This script tries:

1. Skip if already installed (hash-verified)
2. Public HTTPS URL (preferred)
3. ``gh release download`` (logged-in GitHub CLI)
4. GitHub API asset download with GH_TOKEN / GITHUB_TOKEN / ``gh auth token``
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPO = "nizba06/agentguard"
TAG = "v0.1.0"
RELEASE_PAGE = f"https://github.com/{REPO}/releases/download/{TAG}"
API_RELEASE = f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}"
FILES = ("risk_scorer.onnx", "model.sha256")
UA = "inter-agent-guard-demo/0.1.0"


def _package_models_dir() -> Path:
    import agentguard

    return Path(agentguard.__file__).resolve().parent / "models"


def _verify_hash(model_path: Path, hash_path: Path) -> None:
    expected = hash_path.read_text(encoding="utf-8").strip().lower()
    actual = hashlib.sha256(model_path.read_bytes()).hexdigest().lower()
    if actual != expected:
        raise SystemExit(f"ONNX hash mismatch.\n  expected={expected}\n  actual=  {actual}")
    print(f"Hash OK: {actual}")


def _github_token() -> str | None:
    for key in ("GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    gh = shutil.which("gh")
    if not gh:
        return None
    try:
        proc = subprocess.run(
            [gh, "auth", "token"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    token = (proc.stdout or "").strip()
    return token or None


def _download_http(url: str, dest: Path, *, headers: dict[str, str] | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req_headers = {"User-Agent": UA}
    if headers:
        req_headers.update(headers)
    print(f"Downloading {url}")
    print(f"  -> {dest}")
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=600) as resp, dest.open("wb") as out:  # noqa: S310
        shutil.copyfileobj(resp, out)


def _try_public_urls(models_dir: Path) -> bool:
    try:
        for name in FILES:
            _download_http(f"{RELEASE_PAGE}/{name}", models_dir / name)
        return True
    except urllib.error.HTTPError as exc:
        print(f"  public URL failed ({exc.code}); trying authenticated download...")
        return False
    except OSError as exc:
        print(f"  public URL failed ({exc}); trying authenticated download...")
        return False


def _try_gh_cli(models_dir: Path) -> bool:
    gh = shutil.which("gh")
    if not gh:
        return False
    print(f"Using: gh release download {TAG} --repo {REPO}")
    models_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agentguard-onnx-") as tmp:
        tmp_path = Path(tmp)
        cmd = [
            gh,
            "release",
            "download",
            TAG,
            "--repo",
            REPO,
            "--dir",
            str(tmp_path),
            "--clobber",
        ]
        for name in FILES:
            cmd.extend(["--pattern", name])
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            print(f"  gh release download failed: {err or proc.returncode}")
            return False
        for name in FILES:
            src = tmp_path / name
            if not src.is_file():
                print(f"  gh download missing file: {name}")
                return False
            shutil.copy2(src, models_dir / name)
            print(f"  installed {name}")
    return True


def _try_api_token(models_dir: Path) -> bool:
    token = _github_token()
    if not token:
        return False
    print("Using GitHub API + token for release assets...")
    req = urllib.request.Request(
        API_RELEASE,
        headers={
            "User-Agent": UA,
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            release = json.load(resp)
    except (urllib.error.HTTPError, OSError, json.JSONDecodeError) as exc:
        print(f"  API release lookup failed: {exc}")
        return False

    assets = {a["name"]: a for a in release.get("assets", []) if "name" in a and "url" in a}
    for name in FILES:
        asset = assets.get(name)
        if not asset:
            print(f"  API release missing asset: {name}")
            return False
        try:
            _download_http(
                asset["url"],
                models_dir / name,
                headers={
                    "Accept": "application/octet-stream",
                    "Authorization": f"Bearer {token}",
                },
            )
        except (urllib.error.HTTPError, OSError) as exc:
            print(f"  API asset download failed for {name}: {exc}")
            return False
    return True


def _download_all(models_dir: Path) -> None:
    if _try_public_urls(models_dir):
        return
    if _try_gh_cli(models_dir):
        return
    if _try_api_token(models_dir):
        return
    raise SystemExit(
        "Could not download ONNX release assets.\n"
        "  Fix one of:\n"
        "    1. Check network access to GitHub Releases\n"
        "    2. gh auth login   # then re-run: py -3.12 install_model.py\n"
        "    3. set GH_TOKEN or GITHUB_TOKEN with repo read access\n"
        f"  Manual: https://github.com/{REPO}/releases/tag/{TAG}"
    )


def ensure_model(*, force: bool = False) -> Path:
    """Ensure ONNX + SHA are present under the installed agentguard/models/."""
    models_dir = _package_models_dir()
    onnx = models_dir / "risk_scorer.onnx"
    sha = models_dir / "model.sha256"

    if onnx.is_file() and sha.is_file() and not force:
        _verify_hash(onnx, sha)
        print(f"Model already installed: {onnx}")
        return onnx

    _download_all(models_dir)
    _verify_hash(onnx, sha)
    for tok in ("tokenizer.json", "tokenizer_config.json"):
        if not (models_dir / tok).is_file():
            print(f"  WARN  missing {tok} — scorer will fall back to Hugging Face download")
    return onnx


def main() -> int:
    force = "--force" in sys.argv
    path = ensure_model(force=force)
    print(f"Ready: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
