"""
SentinelFlow AI — Idempotency Middleware
Protects state-changing action execution endpoints from accidental double-invocation.
"""

import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from ..core.database import SessionLocal
from ..services.idempotency_service import IdempotencyService
from ..core.observability import logger

class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Intercepts POST requests on action endpoints to ensure idempotency."""

    def __init__(self, app):
        super().__init__(app)
        # Endpoints that require protection
        self.protected_paths = [
            "/approve",
            "/execute-remediation",
            "/execute-command",
            "/remediation-options"
        ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Only apply to state-changing POST requests on protected paths
        is_protected = method == "POST" and any(p in path for p in self.protected_paths)
        if not is_protected:
            return await call_next(request)

        # Retrieve idempotency key
        idem_key = request.headers.get("idempotency-key") or request.headers.get("x-idempotency-key")
        if not idem_key:
            from ..core.config import get_settings
            settings = get_settings()
            if settings.ENVIRONMENT == "testing":
                return await call_next(request)
            return JSONResponse(
                status_code=400,
                content={"detail": "Missing Idempotency-Key header"}
            )

        db = SessionLocal()
        try:
            # 1. Check for cached response
            cached = IdempotencyService.get_cached_response(db, idem_key)
            if cached:
                status_code, body = cached
                if status_code == 202:
                    # Request still in progress
                    return JSONResponse(
                        status_code=409,
                        content={"detail": "Request with this Idempotency-Key is already in progress"}
                    )
                logger.info("idempotency_cache_hit", key=idem_key, path=path)
                return JSONResponse(status_code=status_code, content=body)

            # 2. Register key (mark as processing)
            registered = IdempotencyService.register_key(
                db=db,
                key=idem_key,
                action_type=path
            )
            if not registered:
                return JSONResponse(
                    status_code=409,
                    content={"detail": "Duplicate or concurrent request detected"}
                )

        finally:
            db.close()

        # 3. Call downstream handlers
        try:
            response = await call_next(request)
        except Exception as err:
            # On exception, clear the key so the client can retry
            db = SessionLocal()
            try:
                from ..models.models import IdempotencyKey
                db.query(IdempotencyKey).filter(IdempotencyKey.key == idem_key).delete()
                db.commit()
            finally:
                db.close()
            raise err

        # 4. Extract body and cache successful outcomes (< 400)
        if response.status_code < 400:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            # Reconstruct body iterator so Starlette can send the response
            async def body_iterator():
                yield response_body

            response.body_iterator = body_iterator()

            try:
                body_str = response_body.decode("utf-8")
                body_json = json.loads(body_str) if body_str else {}
                
                # Cache response
                db = SessionLocal()
                try:
                    IdempotencyService.save_response(
                        db=db,
                        key=idem_key,
                        status_code=response.status_code,
                        body=body_json
                    )
                finally:
                    db.close()
            except Exception as parse_err:
                logger.warning("idempotency_body_extract_failed", error=str(parse_err))

        else:
            # If the call failed, delete the key so client can retry with same key
            db = SessionLocal()
            try:
                from ..models.models import IdempotencyKey
                db.query(IdempotencyKey).filter(IdempotencyKey.key == idem_key).delete()
                db.commit()
            finally:
                db.close()

        return response
