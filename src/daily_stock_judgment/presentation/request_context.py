"""HTTP request-scoped logging context (trace_id + OTel-ish HTTP attrs)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = structlog.get_logger("daily_stock_judgment.presentation.request_context")

_TRACE_HEADER = "X-Trace-Id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind trace_id for the request; emit start/end logs; set X-Trace-Id."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            **{
                "trace_id": trace_id,
                "http.request.method": request.method,
                "url.path": request.url.path,
            }
        )
        started = time.perf_counter()
        logger.info("http_request_start")
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            logger.exception(
                "http_request_end",
                **{
                    "http.response.status_code": 500,
                    "duration_ms": duration_ms,
                },
            )
            structlog.contextvars.clear_contextvars()
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        logger.info(
            "http_request_end",
            **{
                "http.response.status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers[_TRACE_HEADER] = trace_id
        structlog.contextvars.clear_contextvars()
        return response
