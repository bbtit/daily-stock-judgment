"""Structured JSON logging (structlog) for local debugging."""

from __future__ import annotations

import logging
import os
import sys

import structlog

_PACKAGE = "daily_stock_judgment"
_CONFIGURED = False

_SHARED_PROCESSORS: tuple[structlog.types.Processor, ...] = (
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
)


def configure_logging(level: str | None = None) -> None:
    """Attach a JSON stderr handler to the package logger (idempotent)."""
    global _CONFIGURED
    resolved = (level or os.environ.get("DSJ_LOG_LEVEL") or "INFO").upper()

    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        # False so tests can reconfigure without stale cached bound loggers.
        cache_logger_on_first_use=False,
    )

    package = logging.getLogger(_PACKAGE)
    package.setLevel(resolved)

    if _CONFIGURED:
        return

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=list(_SHARED_PROCESSORS),
    )
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    package.addHandler(handler)
    # Avoid duplicating through uvicorn's root handlers.
    package.propagate = False
    _CONFIGURED = True


def reset_logging_for_tests() -> None:
    """Drop handlers so the next configure_logging attaches a fresh one."""
    global _CONFIGURED
    package = logging.getLogger(_PACKAGE)
    package.handlers.clear()
    _CONFIGURED = False
    structlog.contextvars.clear_contextvars()
    structlog.reset_defaults()
