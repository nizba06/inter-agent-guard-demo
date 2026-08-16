"""HTTP fixture fetch tool with optional AgentGuard MCP wrapping."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def read_fixture(path: Path) -> str:
    """Read a local HTML fixture and return visible text content."""
    html = path.read_text(encoding="utf-8")
    # Strip tags naively for demo fixtures (small controlled files).
    text = html.replace("<br/>", "\n").replace("<br>", "\n")
    for token in ("<html>", "</html>", "<body>", "</body>", "<h1>", "</h1>", "<p>", "</p>"):
        text = text.replace(token, "")
    return text.strip()


def fetch_url_raw(url: str, *, timeout: float = 10.0) -> str:
    """Fetch URL content over HTTP or read local demo fixtures via ``local://``."""
    if url.startswith("local://"):
        from intelbrief.config import get_settings

        filename = url.removeprefix("local://").lstrip("/")
        path = get_settings().fixtures_dir / filename
        if not path.exists():
            msg = f"Local fixture not found: {path}"
            raise FileNotFoundError(msg)
        return read_fixture(path)

    logger.info("fetch_url_raw url=%s", url)
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    body = response.text
    if "html" in content_type or body.lstrip().startswith("<"):
        return read_fixture_text_from_html(body)
    return body.strip()


def read_fixture_text_from_html(html: str) -> str:
    """Extract readable text from small fixture HTML."""
    text = html.replace("<br/>", "\n").replace("<br>", "\n")
    for token in ("<html>", "</html>", "<body>", "</body>", "<h1>", "</h1>", "<p>", "</p>"):
        text = text.replace(token, "")
    return text.strip()


def build_fetch_tool(guard: Any | None = None) -> Any:
    """Return fetch_url callable, wrapped with AgentGuard when guard is set."""
    if guard is None:
        return fetch_url_raw
    return guard.wrap_mcp_tool(fetch_url_raw, agent_id="researcher")
