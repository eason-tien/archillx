"""
ArcHillx runtime
==============
Standalone autonomous AI execution system.
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse

from .config import settings
from .utils.logging_utils import clear_request_context, configure_logging, set_request_context, structured_log
from .utils.rate_limit import rate_limiter
from .utils.telemetry import telemetry
from .utils.system_health import collect_readiness

configure_logging(settings.log_level)
logger = logging.getLogger("archillx")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ArcHillx v%s starting up...", settings.app_version)

    from .db.schema import init_db
    init_db()
    logger.info("Database ready: %s", settings.database_url)

    from .runtime.skill_manager import skill_manager
    skill_manager.startup()

    from .runtime.cron import cron_system
    cron_system.startup()

    from .evolution.auto_scheduler import evolution_scheduler
    evolution_scheduler.startup()

    from .runtime.heartbeat import heartbeat_writer
    heartbeat_writer.startup()

    from .utils.model_router import model_router
    providers = model_router.list_providers()
    logger.info("AI providers: %s",
                [p["provider"] for p in providers] or ["(none — set API keys in .env)"])

    active_flags = [
        name for name, val in {
            "LMF":              settings.enable_lmf,
            "Planner":          settings.enable_planner,
            "Proactive":        settings.enable_proactive,
            "Notifications":    settings.enable_notifications,
            "Autonomy":         settings.enable_autonomous_remediation,
            "AdaptiveGovernor": settings.enable_adaptive_governor,
            "OpenClaw":         settings.enable_openclaw_integration,
            "TraeSolo":         settings.enable_trae_solo_integration,
            "SkillValidation":  settings.enable_skill_validation,
            "ResourceGuard":    settings.enable_resource_guard,
        }.items() if val
    ]
    if active_flags:
        logger.info("Active feature flags: %s", active_flags)

    logger.info("ArcHillx v%s ready.", settings.app_version)
    yield

    from .runtime.heartbeat import heartbeat_writer
    heartbeat_writer.shutdown()
    from .evolution.auto_scheduler import evolution_scheduler
    evolution_scheduler.shutdown()
    from .runtime.cron import cron_system
    cron_system.shutdown()
    logger.info("ArcHillx shutdown complete.")


app = FastAPI(
    title="ArcHillx",
    version=settings.app_version,
    description=(
        "ArcHillx runtime — Standalone autonomous AI execution system.\n\n"
        "Multi-provider model routing · OODA Loop · Governor · Memory · "
        "Skills · Goals · Cron · LMF · Planner · Autonomy · "
        "Proactive Intelligence · Notifications · OpenClaw · TRAE-Solo"
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.monotonic()
    request.state.request_id = request_id
    tokens = set_request_context(request_id=request_id)
    try:
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        response.headers["x-request-id"] = request_id
        response.headers["x-elapsed-ms"] = str(elapsed_ms)
        telemetry.incr("http_requests_total")
        telemetry.incr(f"http_status_{response.status_code}_total")
        telemetry.timing("http_request", elapsed_ms / 1000.0)
        structured_log(
            logger, logging.INFO, "http_request",
            method=request.method, path=request.url.path, status_code=response.status_code, elapsed_ms=elapsed_ms
        )
        return response
    finally:
        clear_request_context(tokens)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    request.state.auth_role = "anonymous"
    api_key = settings.api_key
    if not api_key:
        return await call_next(request)
    if request.url.path in ("/", "/ui", "/healthz", "/livez", "/readyz", "/metrics", "/v1/health", "/v1/live", "/v1/ready", "/v1/metrics", "/docs",
                             "/redoc", "/openapi.json") or request.url.path.startswith("/ui/static/"):
        return await call_next(request)
    token = (
        request.headers.get("x-api-key")
        or request.headers.get("authorization", "").removeprefix("Bearer ")
    )
    if token not in (api_key, settings.admin_token):
        structured_log(logger, logging.WARNING, "auth_failed", path=request.url.path, method=request.method)
        telemetry.incr("auth_failed_total")
        return JSONResponse({"detail": {"code": "UNAUTHORIZED", "message": "Unauthorized"}}, status_code=401)
    request.state.auth_role = "admin" if token == settings.admin_token and settings.admin_token else "api_key"
    return await call_next(request)




@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not settings.enable_rate_limit:
        return await call_next(request)
    if request.url.path in ("/", "/ui", "/healthz", "/readyz", "/livez", "/v1/health", "/v1/ready", "/v1/live", "/docs", "/redoc", "/openapi.json") or request.url.path.startswith("/ui/static/"):
        return await call_next(request)
    client_host = (request.client.host if request.client else None) or request.headers.get("x-forwarded-for", "unknown").split(",")[0].strip()
    bucket = "default"
    limit = max(1, int(settings.rate_limit_per_min))
    if request.url.path.startswith("/v1/skills/invoke") or request.url.path.startswith("/v1/agent/run"):
        bucket = "high_risk"
        limit = max(1, int(settings.high_risk_rate_limit_per_min))
    result = rate_limiter.check(client_host, bucket=bucket, limit=limit, window_s=60)
    if not result.allowed:
        structured_log(logger, logging.WARNING, "rate_limit_blocked", path=request.url.path, method=request.method, bucket=bucket, client=client_host, limit=result.limit, reset_after_s=result.reset_after_s)
        telemetry.incr("rate_limited_total")
        return JSONResponse(
            {"detail": {"code": "RATE_LIMITED", "message": "Rate limit exceeded", "bucket": bucket, "limit": result.limit, "reset_after_s": result.reset_after_s}},
            status_code=429,
            headers={
                "x-ratelimit-limit": str(result.limit),
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": str(result.reset_after_s),
            },
        )
    response = await call_next(request)
    response.headers["x-ratelimit-limit"] = str(result.limit)
    response.headers["x-ratelimit-remaining"] = str(result.remaining)
    response.headers["x-ratelimit-reset"] = str(result.reset_after_s)
    return response

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    logger.warning("request validation failed: path=%s request_id=%s", request.url.path, getattr(request.state, "request_id", "-"))
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "REQUEST_VALIDATION_FAILED",
                "message": "Request validation failed",
                "errors": exc.errors(),
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("unhandled request error: path=%s request_id=%s", request.url.path, getattr(request.state, "request_id", "-"))
    detail = {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "Unhandled server error",
        "request_id": getattr(request.state, "request_id", None),
    }
    if settings.app_env.strip().lower() in {"dev", "development", "local", "test", "testing"} or settings.expose_internal_error_details:
        detail["reason"] = str(exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": detail
        },
    )


from .api.routes import router as api_router
from .api.evolution_routes import router as evolution_router
from .ui.routes import router as ui_router
app.include_router(api_router, prefix="/v1")
app.include_router(evolution_router, prefix="/v1")
app.include_router(ui_router)
from pathlib import Path as _Path
app.mount("/ui/static", StaticFiles(directory=str((_Path(__file__).resolve().parent / "ui" / "static"))), name="ui-static")

if settings.enable_openclaw_integration:
    from .integrations.openclaw.routes import router as openclaw_router
    app.include_router(openclaw_router)

if settings.enable_trae_solo_integration:
    from .integrations.trae_solo import router as trae_router
    app.include_router(trae_router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "system": "ArcHillx",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/v1/health",
        "ui": "/ui",
    }


@app.get("/healthz", include_in_schema=False)
async def healthz():
    from .utils.model_router import model_router
    return {
        "status": "ok",
        "system": "ArcHillx",
        "version": settings.app_version,
        "ai_providers": model_router.list_providers(),
    }


@app.get("/livez", include_in_schema=False)
async def livez():
    return {"status": "alive", "system": "ArcHillx", "version": settings.app_version}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    payload = collect_readiness()
    payload.update({"system": "ArcHillx", "version": settings.app_version})
    code = 200 if payload["status"] == "ready" else 503
    return JSONResponse(payload, status_code=code)


@app.get("/metrics", include_in_schema=False)
async def metrics_root():
    if not settings.enable_metrics:
        return JSONResponse({"detail": {"code": "METRICS_DISABLED", "message": "Metrics are disabled"}}, status_code=503)
    return PlainTextResponse(telemetry.as_prometheus(), media_type="text/plain; version=0.0.4")
