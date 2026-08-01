"""Package logging for local debugging (uvicorn access logs alone are not enough)."""

from __future__ import annotations

import logging
import os

_PACKAGE = "daily_stock_judgment"
_CONFIGURED = False


def configure_logging(level: str | None = None) -> None:
    """Attach a stderr handler to the package logger (idempotent)."""
    global _CONFIGURED
    resolved = (level or os.environ.get("DSJ_LOG_LEVEL") or "INFO").upper()
    package = logging.getLogger(_PACKAGE)
    package.setLevel(resolved)

    if _CONFIGURED:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    package.addHandler(handler)
    # Avoid duplicating through uvicorn's root handlers.
    package.propagate = False
    _CONFIGURED = True
