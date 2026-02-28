"""
ArcHillx v1.0.0
==============
Standalone autonomous AI execution system.

Architecture:
  Multi-provider model routing  (Anthropic / OpenAI / Google / Groq / Mistral / OLLAMA / Custom)
  OODA Loop                     (Observe → Orient → Decide → Act → Learn)
  Governor                      (rule-based risk scoring, soft/hard block)
  Memory Store                  (keyword-searchable SQLite, tag filter)
  Skill Manager                 (local Python skills, OpenClaw-manifest compatible)
  Goal Tracker                  (cross-session long-term goal 0.0–1.0)
  Lifecycle Manager             (Session / Task / Agent state machines)
  Cron System                   (APScheduler, cron + interval, DB persistent)
  Evidence Logs                 (JSONL audit trail)
  LMF                           (5-tier Language Memory Framework)
  Planner                       (hierarchical task-graph planning)
  Autonomy                      (tier-classified remediation + canary rollout)
  Proactive Intelligence        (daily driver + sprint planner)
  Notifications                 (Slack / Telegram / Webhook / WebSocket)
  Integrations                  (OpenClaw gateway / TRAE-Solo coding agent)

API:
  GET  /v1/health
  GET  /v1/models
  POST /v1/agent/run
  GET  /v1/agent/tasks
  GET  /v1/skills
  POST /v1/skills/invoke
  GET  /v1/goals
  POST /v1/goals
  GET  /v1/sessions
  GET  /v1/memory/search
  POST /v1/memory
  GET  /v1/cron
  POST /v1/cron
  /v1/lmf/*                     (feature-gated)
  /v1/planner/*                 (feature-gated)
  /v1/proactive/*               (feature-gated)
  /v1/notifications/*           (feature-gated)
  /v1/integrations/openclaw/*   (feature-gated)
  /v1/integrations/trae/*       (feature-gated)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("archillx")


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ArcHillx v%s starting up...", settings.app_version)

    # 1. Init database
    from .db.schema import init_db
    init_db()
    logger.info("Database ready: %s", settings.database_url)

    # 2. Load skills
    from .runtime.skill_manager import skill_manager
    skill_manager.startup()

    # 3. Start cron
    from .runtime.cron import cron_system
    cron_system.startup()

    # 4. Log active AI providers
    from .utils.model_router import model_router
    providers = model_router.list_providers()
    logger.info("AI providers: %s",
                [p["provider"] for p in providers] or ["(none — set API keys in .env)"])

    # 5. Log active feature flags
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
            "SelfHealing":      settings.enable_self_healing,
        }.items() if val
    ]
    if active_flags:
        logger.info("Active feature flags: %s", active_flags)

    logger.info("ArcHillx v%s ready.", settings.app_version)
    yield

    # Shutdown
    from .runtime.cron import cron_system
    cron_system.shutdown()
    logger.info("ArcHillx shutdown complete.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ArcHillx",
    version="1.0.0",
    description=(
        "ArcHillx v1.0.0 — Standalone autonomous AI execution system.\n\n"
        "Multi-provider model routing · OODA Loop · Governor · Memory · "
        "Skills · Goals · Cron · LMF · Planner · Autonomy · "
        "Proactive Intelligence · Notifications · OpenClaw · TRAE-Solo"
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Auth middleware (optional) ────────────────────────────────────────────────

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    api_key = settings.api_key
    if not api_key:
        return await call_next(request)
    # Skip health / docs
    if request.url.path in ("/", "/healthz", "/v1/health", "/docs",
                             "/redoc", "/openapi.json"):
        return await call_next(request)
    token = (
        request.headers.get("x-api-key")
        or request.headers.get("authorization", "").removeprefix("Bearer ")
    )
    if token not in (api_key, settings.admin_token):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


# ── Core routes ───────────────────────────────────────────────────────────────

from .api.routes import router as api_router
app.include_router(api_router, prefix="/v1")

# ── Feature-gated: OpenClaw integration ──────────────────────────────────────

from .integrations.openclaw.routes import router as openclaw_router
app.include_router(openclaw_router)

# ── Feature-gated: TRAE-Solo integration ─────────────────────────────────────

from .integrations.trae_solo import router as trae_router
app.include_router(trae_router)


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {
        "system": "ArcHillx",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/v1/health",
    }


@app.get("/healthz", include_in_schema=False)
async def healthz():
    from .utils.model_router import model_router
    return {
        "status": "ok",
        "system": "ArcHillx",
        "version": "1.0.0",
        "ai_providers": model_router.list_providers(),
    }
