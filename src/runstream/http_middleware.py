from __future__ import annotations

import logging
import os
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("runstream.access")

# Shared bucket for rate limiting (cleared in tests via clear_rate_limit_state_for_tests).
_rate_limit_hits: dict[str, list[float]] = defaultdict(list)


def clear_rate_limit_state_for_tests() -> None:
    _rate_limit_hits.clear()


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Structured-ish one-line access log (disable with RUNSTREAM_DISABLE_ACCESS_LOG=1)."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        if _env_truthy("RUNSTREAM_DISABLE_ACCESS_LOG"):
            return await call_next(request)
        t0 = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - t0) * 1000
        client = request.client.host if request.client else "-"
        logger.info(
            "%s %s %s %d %.2fms",
            client,
            request.method,
            request.url.path,
            response.status_code,
            ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window per client IP when RUNSTREAM_ENABLE_RATE_LIMIT=1.
    RUNSTREAM_RATE_LIMIT_RPM (default 120). /health is exempt.
    """

    def _rpm(self) -> int:
        try:
            return max(1, int(os.getenv("RUNSTREAM_RATE_LIMIT_RPM", "120")))
        except ValueError:
            return 120

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        if not _env_truthy("RUNSTREAM_ENABLE_RATE_LIMIT"):
            return await call_next(request)
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        now = time.monotonic()
        window = 60.0
        rpm = self._rpm()
        ip = request.client.host if request.client else "unknown"

        bucket = _rate_limit_hits[ip]
        bucket[:] = [t for t in bucket if now - t < window]
        if len(bucket) >= rpm:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded", "retry_after_sec": 60},
            )
        bucket.append(now)

        return await call_next(request)
