"""
SentinelFlow AI — Main FastAPI Application
Entry point that wires up all routers, middleware, database init, and startup events.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .schemas.schemas import ErrorResponse, ErrorDetail
from .core.config import get_settings
from .core.database import Base, engine, SessionLocal, init_db
from .core.vector_db import init_qdrant_collections
from .core.websocket import ws_manager
from .core.observability import instrument_app, logger
from .middleware.gateway import APIGatewayMiddleware
from .api.router_auth import router as auth_router
from .api.router_telemetry import router as telemetry_router
from .api.router_incidents import router as incidents_router
from .api.router_agent import router as agent_router
from .api.router_infra import router as infra_router
from .api.router_integrations import router as integrations_router
from .api.router_flags import router as flags_router
from .api.router_ops import router as ops_router
from .api.router_demo import router as demo_router
from .api.router_websocket import router as websocket_router
from .api.router_knowledge import router as knowledge_router
from .api.router_security import router as security_router

settings = get_settings()


# ── Lifespan (startup/shutdown) ──────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # ── Startup ──────────────────────────────────────────────
    logger.info("startup_begin", project=settings.PROJECT_NAME, version="1.0.0")

    # Initialize database tables
    init_db()
    logger.info("database_initialized")

    # Initialize Qdrant vector collections
    init_qdrant_collections()

    # Seed default data
    db = SessionLocal()
    try:
        from .services.auth_service import seed_default_users
        seed_default_users(db)

        from .services.workflow_service import seed_prompt_templates
        seed_prompt_templates(db)

        from .services.policy_engine import PolicyEngine
        PolicyEngine.seed_default_policies(db)

        from .models.models import ExecutionConfig
        if not db.query(ExecutionConfig).first():
            config = ExecutionConfig(
                id=1,
                mode="MANUAL",
                rate_limit_per_minute=5,
                min_confidence_score=90,
                max_blast_radius=10,
                restricted_services="payment",
                low_risk_actions="restart_pod,scale_service,rollout_restart"
            )
            db.add(config)
            db.commit()
            logger.info("execution_config_seeded")
    finally:
        db.close()

    # Start background simulator
    if settings.FF_DEMO_MODE:
        from .services.simulator_service import start_simulator_thread
        start_simulator_thread()

    logger.info(
        "startup_complete",
        project=settings.PROJECT_NAME,
        docs_url=f"http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}/docs",
    )

    # ── Phase 57: Start Live Metrics Broadcast Loop ──────────────────
    import asyncio

    async def _live_metrics_broadcast_loop():
        """Capture + broadcast cluster metrics every 5 seconds to all WS clients."""
        from .services.metrics_dashboard_service import MetricsDashboardService
        from .services.websocket_service import broadcast_live_metrics_update

        while True:
            try:
                await asyncio.sleep(5)
                payload = MetricsDashboardService.capture_snapshot()
                broadcast_live_metrics_update(payload)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("live_metrics_broadcast_error", error=str(exc))

    metrics_task = asyncio.create_task(_live_metrics_broadcast_loop())
    logger.info("live_metrics_broadcast_started", interval_seconds=5)

    yield

    # ── Shutdown ─────────────────────────────────────────────
    metrics_task.cancel()
    try:
        await metrics_task
    except asyncio.CancelledError:
        pass
    logger.info("shutdown", project=settings.PROJECT_NAME)


# ── App Factory ──────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous AI-Driven Incident Response Platform for Kubernetes Infrastructure",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

instrument_app(app)

from .core.tracing import TracingService
TracingService.initialize_tracing(app)

# Resolve allowed origins
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
if not origins or "*" in origins:
    origins = ["*"]

from .middleware.idempotency_middleware import IdempotencyMiddleware

# ── Middleware Stack ─────────────────────────────────────────
# Order matters: last added = first executed
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(APIGatewayMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True if origins != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Inject production security headers following OWASP/HSTS recommendations."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' ws: wss:;"
    )
    return response


# ── Global Exception Handlers ────────────────────────────────
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Standardized handler for HTTPExceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            code="HTTP_EXCEPTION",
        ).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Standardized handler for RequestValidationErrors."""
    errors = [
        ErrorDetail(
            loc=[str(loc_part) for loc_part in err["loc"]],
            msg=err["msg"],
            type=err["type"]
        )
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            detail="Request validation failed",
            errors=errors,
            code="VALIDATION_ERROR"
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Standardized handler for all uncaught server exceptions."""
    logger.error(
        "unhandled_exception",
        method=request.method,
        path=request.url.path,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            detail="An unexpected error occurred on the server.",
            code="INTERNAL_SERVER_ERROR"
        ).model_dump()
    )


# ── API Routers ──────────────────────────────────────────────
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(telemetry_router, prefix=settings.API_V1_PREFIX)
app.include_router(incidents_router, prefix=settings.API_V1_PREFIX)
app.include_router(agent_router, prefix=settings.API_V1_PREFIX)
app.include_router(infra_router, prefix=settings.API_V1_PREFIX)
app.include_router(integrations_router, prefix=settings.API_V1_PREFIX)
app.include_router(flags_router, prefix=settings.API_V1_PREFIX)
app.include_router(demo_router, prefix=settings.API_V1_PREFIX)
app.include_router(websocket_router, prefix=settings.API_V1_PREFIX)
app.include_router(knowledge_router, prefix=settings.API_V1_PREFIX)
app.include_router(security_router, prefix=settings.API_V1_PREFIX)
app.include_router(ops_router, prefix=settings.API_V1_PREFIX)


# ── WebSocket Endpoint ──────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for heartbeat/ping
            await ws_manager.send_to(websocket, "pong", {"received": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ── Health Check ─────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health_check():
    """Root health check endpoint."""
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "api_docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def detailed_health():
    """Detailed health check with service status."""
    from .core.redis_streams import REDIS_AVAILABLE
    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "redis": "connected" if REDIS_AVAILABLE else "fallback (in-memory)",
            "qdrant": "connected (local)",
            "simulator": "running" if settings.FF_DEMO_MODE else "disabled",
            "websocket": f"{len(ws_manager.active_connections)} clients",
        },
    }


@app.get("/health/live", tags=["Health"])
def health_live():
    """Liveness probe checkpoint."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def health_ready():
    """Readiness probe checkpoint."""
    return {"status": "ready"}
