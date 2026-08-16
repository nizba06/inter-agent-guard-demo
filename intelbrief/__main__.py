"""CLI entrypoint: uvicorn intelbrief.api.app:app"""

from __future__ import annotations

import uvicorn

from intelbrief.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "intelbrief.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
