"""
SentinelFlow AI — API Gateway Middleware
Rate limiting, OWASP injection protection, and request logging.
"""

import re
import time
import uuid
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..core.config import get_settings
from ..core.observability import logger

settings = get_settings()

# ── OWASP Injection Patterns ────────────────────────────────
INJECTION_PATTERNS = [
    re.compile(r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|EXECUTE)\b.*\b(FROM|INTO|TABLE|DATABASE)\b)", re.IGNORECASE),
    re.compile(r"(--|;|/\*|\*/|xp_|sp_)", re.IGNORECASE),
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
]

# Paths exempt from rate limiting
RATE_LIMIT_EXEMPT = frozenset({
    "/docs", "/redoc", "/openapi.json", "/",
    "/api/v1/telemetry/ingest",  # High-throughput endpoint
    "/ws",  # WebSocket connections
})


class APIGatewayMiddleware(BaseHTTPMiddleware):
    """
    Combined API Gateway providing:
    1. Rate limiting (token bucket per IP)
    2. OWASP injection protection
    3. Request timing headers
    """

    def __init__(self, app):
        super().__init__(app)
        self._rate_buckets: dict[str, list[float]] = defaultdict(list)
        self._max_requests = settings.RATE_LIMIT_REQUESTS
        self._window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # ── 1. Correlation ID Injection ───────────────────────
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = f"sf-trace-{uuid.uuid4().hex[:12]}"
        request.state.correlation_id = correlation_id

        # ── 2. Request Logging ────────────────────────────────
        logger.debug(
            "gateway_request",
            method=request.method,
            path=path,
            correlation_id=correlation_id,
            client_ip=client_ip,
        )

        # ── 3. HTTPS Check & Warning ──────────────────────────
        is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"

        # ── 4. Rate Limiting ──────────────────────────────────
        if settings.ENVIRONMENT != "testing" and path not in RATE_LIMIT_EXEMPT and not path.startswith("/ws"):
            now = time.time()
            bucket = self._rate_buckets[client_ip]
            bucket[:] = [t for t in bucket if now - t < self._window_seconds]
            if len(bucket) >= self._max_requests:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after_seconds": self._window_seconds,
                    },
                )
            bucket.append(now)

        # ── 5. Injection Protection ───────────────────────────
        query_string = str(request.url.query) if request.url.query else ""
        for pattern in INJECTION_PATTERNS:
            if pattern.search(query_string):
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Potentially malicious input detected"},
                )

        # ── 6. Process Request ────────────────────────────────
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(
                "gateway_error",
                method=request.method,
                path=path,
                error=str(e),
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error. Logged by Gateway."},
            )

        # ── 7. Timing & Correlation Headers ───────────────────
        duration_ms = (time.time() - start_time) * 1000
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self._max_requests - len(self._rate_buckets.get(client_ip, [])))
        )

        # ── 8. Security Headers ───────────────────────────────
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer"

        if settings.ENVIRONMENT == "production" and not is_https:
            response.headers["X-Security-Warning"] = "Insecure HTTP connection in production environment!"

        if is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # ── 9. Response Logging ───────────────────────────────
        logger.debug(
            "gateway_response",
            method=request.method,
            path=path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 1),
            correlation_id=correlation_id,
        )

        return response
