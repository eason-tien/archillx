"""
ArcHillx v1.0.0 — API Routes  /v1/*
"""
from __future__ import annotations

from typing import Any, Optional
from datetime import datetime
from pathlib import Path

import logging
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from pydantic import BaseModel, Field

from ..utils.api_errors import bad_request, internal_error, not_found, service_unavailable
from ..utils.logging_utils import bind_runtime_context, structured_log
from ..utils.telemetry import telemetry
from ..utils.system_health import collect_readiness
from ..evolution.signal_collector import _gate_summary
from ..config import settings
from ..entropy.engine import entropy_engine

logger = logging.getLogger("archillx.api")

router = APIRouter()


def _latest_artifact_group(directory: Path, prefix: str) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    variants = {"json": None, "markdown": None, "html": None}
    latest_path_obj = None
    for suffix, ext in (("json", ".json"), ("markdown", ".md"), ("html", ".html")):
        matches = sorted(directory.glob(f"{prefix}_*{ext}"))
        if matches:
            variants[suffix] = str(matches[-1])
            if latest_path_obj is None or matches[-1].stat().st_mtime > latest_path_obj.stat().st_mtime:
                latest_path_obj = matches[-1]
    latest = next((v for v in variants.values() if v), None)
    updated_at = None
    if latest_path_obj is not None:
        try:
            updated_at = datetime.utcfromtimestamp(latest_path_obj.stat().st_mtime).isoformat() + "Z"
        except Exception:
            updated_at = None
    return {"latest": latest, "paths": variants, "updated_at": updated_at}


def _latest_restore_drill_report() -> dict[str, Any]:
    drills_dir = Path('evidence/drills')
    drills_dir.mkdir(parents=True, exist_ok=True)
    matches = sorted(drills_dir.glob('restore_drill_*.json'))
    if not matches:
        return {"available": False, "latest": None, "report": None}
    latest = matches[-1]
    try:
        import json
        payload = json.loads(latest.read_text(encoding='utf-8'))
    except Exception as e:
        payload = {"error": str(e)}
    updated_at = None
    try:
        updated_at = datetime.utcfromtimestamp(latest.stat().st_mtime).isoformat() + "Z"
    except Exception:
        updated_at = None
    return {"available": True, "latest": str(latest), "report": payload, "updated_at": updated_at}


# ── Request / Response Models ─────────────────────────────────────────────────

class AgentRunReq(BaseModel):
    command: str
    source: str = "user"
    session_id: Optional[int] = None
    goal_id: Optional[int] = None
    context: dict = Field(default_factory=dict)
    skill_hint: Optional[str] = None
    task_type: str = "general"
    budget: str = "medium"


class AgentRunResp(BaseModel):
    success: bool
    task_id: Optional[int]
    skill_used: Optional[str]
    provider_model: Optional[str] = Field(default=None, alias="model_used")
    output: Any
    tokens_used: int
    elapsed_s: float
    governor_approved: bool
    error: Optional[str] = None
    memory_hits: list = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
    }


class GoalCreateReq(BaseModel):
    title: str
    description: str = ""
    priority: int = 5
    context: dict = Field(default_factory=dict)


class GoalUpdateReq(BaseModel):
    progress: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None   # active|paused|completed|abandoned


class SkillInvokeReq(BaseModel):
    name: str
    inputs: dict = Field(default_factory=dict)


class CronAddReq(BaseModel):
    name: str
    skill_name: str
    cron_expr: Optional[str] = None
    interval_s: Optional[int] = None
    input_data: dict = Field(default_factory=dict)
    governor_required: bool = True


class SessionCreateReq(BaseModel):
    name: str
    context: dict = Field(default_factory=dict)


class MemoryAddReq(BaseModel):
    content: str
    source: str = "user"
    tags: list[str] = Field(default_factory=list)
    importance: float = 0.5
    metadata: dict = Field(default_factory=dict)


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", tags=["system"])
async def health():
    from ..utils.model_router import model_router
    from ..runtime.skill_manager import skill_manager
    from ..runtime.cron import cron_system
    return {
        "status": "ok",
        "system": "ArcHillx",
        "version": settings.app_version,
        "ai_providers": model_router.list_providers(),
        "loaded_skills": [s["name"] for s in skill_manager.list_skills()],
        "cron_active": cron_system._started,
    }


@router.get("/models", tags=["system"])
async def list_models():
    from ..utils.model_router import model_router
    return {"providers": model_router.list_providers(),
            "available": model_router.available_providers()}


@router.get("/live", tags=["system"])
async def live():
    return {"status": "alive", "system": "ArcHillx", "version": settings.app_version}


@router.get("/ready", tags=["system"])
async def ready():
    payload = collect_readiness()
    payload.update({"system": "ArcHillx", "version": settings.app_version})
    code = 200 if payload["status"] == "ready" else 503
    return JSONResponse(payload, status_code=code)


@router.get("/system/monitor", tags=["system"])
async def system_monitor():
    import os
    import platform
    import tempfile
    import time
    import json
    from pathlib import Path as _Path

    health_payload = await health()
    ready_payload = collect_readiness()
    migration_payload = await migration_state()
    migration_body = migration_payload.body.decode("utf-8") if hasattr(migration_payload, "body") else "{}"
    try:
        migration_json = json.loads(migration_body)
    except Exception:
        migration_json = {"raw": migration_body}

    hb_path = _Path(settings.recovery_heartbeat_path) if settings.recovery_heartbeat_path else (_Path(tempfile.gettempdir()) / "archillx_heartbeat.json")
    state_path = _Path(tempfile.gettempdir()) / "archillx_recovery_state.json"
    handoff_path = _Path(settings.recovery_handoff_path) if settings.recovery_handoff_path else (_Path(tempfile.gettempdir()) / "archillx_handoff.json")
    lock_meta_path = _Path(tempfile.gettempdir()) / "archillx_recovery.lock.json"

    def _load_json(path: _Path) -> dict:
        if not path.exists():
            return {"exists": False, "path": str(path)}
        try:
            return {"exists": True, "path": str(path), "payload": json.loads(path.read_text(encoding="utf-8"))}
        except Exception as e:
            return {"exists": True, "path": str(path), "error": str(e)}

    hb_data = _load_json(hb_path)
    age = None
    if hb_data.get("exists") and isinstance(hb_data.get("payload"), dict):
        epoch = hb_data["payload"].get("epoch")
        if isinstance(epoch, (int, float)):
            age = max(0.0, time.time() - float(epoch))

    telemetry_payload = {
        "snapshot": telemetry.snapshot(),
        "aggregate": telemetry.aggregated_snapshot(),
        "history_size": len(telemetry.history_snapshot() or []),
    }

    return {
        "system": "ArcHillx",
        "version": settings.app_version,
        "app_env": settings.app_env,
        "host": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "pid": os.getpid(),
        },
        "health": health_payload,
        "ready": ready_payload,
        "migration": migration_json,
        "recovery": {
            "enabled": settings.recovery_enabled,
            "mode": settings.recovery_mode,
            "lock_backend": settings.recovery_lock_backend,
            "heartbeat_ttl_s": settings.recovery_heartbeat_ttl_s,
            "heartbeat_age_s": age,
            "heartbeat": hb_data,
            "state": _load_json(state_path),
            "handoff": _load_json(handoff_path),
            "lock_meta": _load_json(lock_meta_path),
        },
        "telemetry": telemetry_payload,
        "entropy": entropy_engine.evaluate(persist=False),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/entropy/status", tags=["entropy"])
async def entropy_status():
    return entropy_engine.status()


@router.post("/entropy/tick", tags=["entropy"])
async def entropy_tick():
    return entropy_engine.evaluate(persist=True)


@router.get("/metrics", tags=["system"])
async def metrics():
    from ..config import settings
    if not settings.enable_metrics:
        raise service_unavailable("METRICS_DISABLED", "Metrics are disabled")
    return PlainTextResponse(telemetry.as_prometheus(), media_type="text/plain; version=0.0.4")


@router.get("/telemetry", tags=["system"])
async def telemetry_snapshot():
    from ..config import settings
    if not settings.enable_telemetry:
        raise service_unavailable("TELEMETRY_DISABLED", "Telemetry is disabled. Set ENABLE_TELEMETRY=true")
    return {"service": settings.telemetry_service_name, "snapshot": telemetry.snapshot(), "aggregate": telemetry.aggregated_snapshot(), "history": telemetry.history_snapshot()}


@router.get("/migration/state", tags=["system"])
async def migration_state():
    from ..utils.migration_state import get_migration_state
    payload = get_migration_state()
    code = 200 if payload.get("ok", False) else 503
    return JSONResponse(payload, status_code=code)


@router.get("/gates/summary", tags=["system"])
async def gates_summary(limit: int = Query(20, ge=1, le=200)):
    payload = _gate_summary(limit)
    return {"service": "ArcHillx", "limit": limit, "summary": payload}


@router.get("/restore-drill/latest", tags=["system"])
async def restore_drill_latest():
    payload = _latest_restore_drill_report()
    code = 200 if payload.get("available") else 404
    return JSONResponse(payload, status_code=code)


@router.get("/restore-drill/preview", tags=["system"], response_class=HTMLResponse)
async def restore_drill_preview():
    return HTMLResponse(_render_restore_preview_html(_latest_restore_drill_report()))


@router.get("/gates/portal/latest", tags=["system"])
async def gates_portal_latest():
    payload = _latest_artifact_group(Path('evidence/dashboards'), 'gate_summary')
    return {"service": "ArcHillx", "portal": payload}


@router.get("/gates/portal/preview", tags=["system"], response_class=HTMLResponse)
async def gates_portal_preview():
    return HTMLResponse(_render_gate_portal_html({"summary": _gate_summary(20)}))






def _render_gate_portal_html(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    release = summary.get("release") or {}
    rollback = summary.get("rollback") or {}
    latest = summary.get("latest_paths") or {}
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Gate portal preview</title>"
        "<style>body{font-family:Arial,sans-serif;margin:24px;line-height:1.45}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.card{border:1px solid #ddd;border-radius:12px;padding:16px}pre{background:#f7f7f7;padding:12px;border-radius:8px;overflow:auto;white-space:pre-wrap}</style></head><body>"
        f"<h1>Gate portal preview</h1><div class='grid'><div class='card'><h3>Release</h3><div>Passed: {release.get('passed',0)} / {release.get('total',0)}</div><div>Failed: {release.get('failed',0)}</div></div>"
        f"<div class='card'><h3>Rollback</h3><div>Passed: {rollback.get('passed',0)} / {rollback.get('total',0)}</div><div>Failed: {rollback.get('failed',0)}</div></div></div>"
        f"<h2>Latest evidence paths</h2><pre>{latest}</pre></body></html>"
    )


def _render_restore_preview_html(payload: dict[str, Any]) -> str:
    report = payload.get('report') or {}
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Restore drill preview</title>"
        "<style>body{font-family:Arial,sans-serif;margin:24px;line-height:1.45}.card{border:1px solid #ddd;border-radius:12px;padding:16px;max-width:720px}pre{background:#f7f7f7;padding:12px;border-radius:8px;overflow:auto;white-space:pre-wrap}</style></head><body>"
        f"<h1>Restore drill preview</h1><div class='card'><div><strong>Available:</strong> {payload.get('available')}</div><div><strong>Latest:</strong> {payload.get('latest')}</div></div>"
        f"<h2>Report</h2><pre>{report}</pre></body></html>"
    )

def _status_bucket_from_ratio(passed: int, total: int) -> str:
    if total <= 0:
        return "unknown"
    if passed == total:
        return "good"
    if passed == 0:
        return "bad"
    return "warn"


def _restore_bucket(payload: dict[str, Any]) -> str:
    if not payload.get("available"):
        return "bad"
    report = payload.get("report") or {}
    if report.get("status") in ("ok", "passed", "success"):
        return "good"
    return "warn"


@router.get("/system/overview-status", tags=["system"])
async def system_overview_status(limit: int = Query(20, ge=1, le=200)):
    from ..utils.migration_state import get_migration_state
    try:
        from ..evolution.service import evolution_service
        evo_summary = evolution_service.summary(limit=limit)
        evo_status = evolution_service.status()
    except Exception:
        evo_summary = {}
        evo_status = {}
    gates = _gate_summary(limit)
    migration = get_migration_state()
    restore = _latest_restore_drill_report()

    release = gates.get("release") or {}
    rollback = gates.get("rollback") or {}
    evolution_pipeline = (evo_summary or {}).get("pipeline") or {}

    payload = {
        "service": "ArcHillx",
        "limit": limit,
        "sections": {
            "release": {
                "status": _status_bucket_from_ratio(int(release.get("passed", 0) or 0), int(release.get("total", 0) or 0)),
                "passed": int(release.get("passed", 0) or 0),
                "total": int(release.get("total", 0) or 0),
                "latest_paths": gates.get("latest_paths") or [],
                "last_updated": release.get("updated_at"),
                "timeline": [
                    {"label": "release gate", "value": release.get("updated_at") or "no timestamp"},
                    {"label": "evidence count", "value": len(gates.get("latest_paths") or [])},
                ],
            },
            "rollback": {
                "status": _status_bucket_from_ratio(int(rollback.get("passed", 0) or 0), int(rollback.get("total", 0) or 0)),
                "passed": int(rollback.get("passed", 0) or 0),
                "total": int(rollback.get("total", 0) or 0),
                "latest_paths": gates.get("latest_paths") or [],
                "last_updated": rollback.get("updated_at"),
                "timeline": [
                    {"label": "rollback gate", "value": rollback.get("updated_at") or "no timestamp"},
                    {"label": "evidence count", "value": len(gates.get("latest_paths") or [])},
                ],
            },
            "restore": {
                "status": _restore_bucket(restore),
                "available": bool(restore.get("available")),
                "latest": restore.get("latest"),
                "report": restore.get("report"),
                "last_updated": restore.get("updated_at"),
                "timeline": [
                    {"label": "latest report", "value": restore.get("latest") or "no report"},
                    {"label": "report status", "value": (restore.get("report") or {}).get("status") or "unknown"},
                ],
            },
            "migration": {
                "status": migration.get("status", "unknown"),
                "ok": bool(migration.get("ok")),
                "current": migration.get("current"),
                "head": migration.get("head"),
                "last_updated": datetime.utcnow().isoformat() + "Z",
            },
            "evolution": {
                "status": "good" if (evo_summary or {}).get("counts", {}).get("proposals", 0) or evolution_pipeline.get("approved_or_applied", 0) else "warn",
                "pending_approval": evolution_pipeline.get("pending_approval", 0),
                "actionable": evolution_pipeline.get("actionable", 0),
                "guard_pass_rate": evolution_pipeline.get("guard_pass_rate", 0),
                "regression_rate": evolution_pipeline.get("regression_rate", 0),
                "latest_schedule": (evo_status or {}).get("schedule"),
                "last_updated": ((evo_status or {}).get("action") or {}).get("created_at") or ((evo_status or {}).get("baseline") or {}).get("created_at") or ((evo_status or {}).get("guard") or {}).get("created_at") or ((evo_status or {}).get("proposal") or {}).get("created_at") or ((evo_status or {}).get("plan") or {}).get("created_at") or ((evo_status or {}).get("inspection") or {}).get("created_at"),
                "timeline": [
                    {"label": "latest proposal", "value": ((evo_status or {}).get("proposal") or {}).get("proposal_id") or "none"},
                    {"label": "latest action", "value": ((evo_status or {}).get("action") or {}).get("action") or "none"},
                    {"label": "latest schedule", "value": (((evo_status or {}).get("schedule") or {}).get("cycle_id") or "none")},
                ],
            },
        }
    }
    return payload

# ── Agent (OODA) ──────────────────────────────────────────────────────────────

@router.post("/agent/run", response_model=AgentRunResp, tags=["agent"])
async def agent_run(req: AgentRunReq):
    """Execute one full OODA cycle: Observe → Orient → Decide → Act → Learn"""
    try:
        from ..loop.main_loop import main_loop, LoopInput
        bind_runtime_context(session_id=req.session_id)
        result = main_loop.run(LoopInput(
            command=req.command, source=req.source,
            session_id=req.session_id, goal_id=req.goal_id,
            context=req.context, skill_hint=req.skill_hint,
            task_type=req.task_type, budget=req.budget,
        ))
        bind_runtime_context(session_id=req.session_id, task_id=result.task_id)
        structured_log(logger, logging.INFO, "agent_run_completed", success=result.success, skill_used=result.skill_used, model_used=result.model_used, tokens_used=result.tokens_used)
        return AgentRunResp(
            success=result.success, task_id=result.task_id,
            skill_used=result.skill_used, provider_model=result.model_used,
            output=result.output, tokens_used=result.tokens_used,
            elapsed_s=result.elapsed_s, governor_approved=result.governor_approved,
            error=result.error, memory_hits=result.memory_hits,
        )
    except ValueError as e:
        logger.warning("agent_run invalid input: %s", e)
        raise bad_request("AGENT_RUN_INVALID", str(e))
    except Exception as e:
        logger.exception("agent_run failed")
        raise internal_error("AGENT_RUN_FAILED", "Agent execution failed", {"reason": str(e)})


@router.get("/agent/tasks", tags=["agent"])
async def list_tasks(limit: int = 20):
    from ..runtime.lifecycle import lifecycle
    return {"tasks": lifecycle.tasks.list_recent(limit)}


@router.get("/agent/tasks/{task_id}", tags=["agent"])
async def get_task(task_id: int):
    from ..runtime.lifecycle import lifecycle
    t = lifecycle.tasks.get(task_id)
    if not t:
        raise not_found("TASK_NOT_FOUND", "Task not found", {"task_id": task_id})
    return t


# ── Skills ────────────────────────────────────────────────────────────────────

@router.get("/skills", tags=["skills"])
async def list_skills():
    from ..runtime.skill_manager import skill_manager
    return {"skills": skill_manager.list_skills()}


@router.post("/skills/invoke", tags=["skills"])
async def invoke_skill(req: SkillInvokeReq, request: Request):
    from ..runtime.skill_manager import skill_manager, SkillNotFound, SkillValidationError, SkillDisabled, SkillAccessDenied
    try:
        role = getattr(request.state, "auth_role", "anonymous")
        return skill_manager.invoke(req.name, req.inputs, context={"source": "api", "role": role})
    except SkillNotFound as e:
        raise not_found("SKILL_NOT_FOUND", str(e))
    except SkillValidationError as e:
        raise bad_request("SKILL_INPUT_INVALID", str(e), {"name": req.name})
    except SkillDisabled as e:
        raise service_unavailable("SKILL_DISABLED", str(e), {"name": req.name})
    except SkillAccessDenied as e:
        raise bad_request("SKILL_ACCESS_DENIED", str(e), {"name": req.name})
    except ValueError as e:
        raise bad_request("SKILL_INVALID", str(e), {"name": req.name})
    except Exception as e:
        logger.exception("skill invoke failed: %s", req.name)
        raise internal_error("SKILL_INVOKE_FAILED", "Failed to invoke skill", {"name": req.name, "reason": str(e)})


# ── Goals ─────────────────────────────────────────────────────────────────────

@router.get("/goals", tags=["goals"])
async def list_goals(status: Optional[str] = None):
    from ..loop.goal_tracker import goal_tracker
    return {"goals": goal_tracker.list_active() if status == "active"
            else goal_tracker.list_all()}


@router.post("/goals", tags=["goals"])
async def create_goal(req: GoalCreateReq):
    from ..loop.goal_tracker import goal_tracker
    gid = goal_tracker.create(req.title, req.description,
                               req.priority, req.context)
    return {"goal_id": gid}


@router.patch("/goals/{goal_id}", tags=["goals"])
async def update_goal(goal_id: int, req: GoalUpdateReq):
    from ..loop.goal_tracker import goal_tracker
    g = goal_tracker.get(goal_id)
    if not g:
        raise not_found("GOAL_NOT_FOUND", "Goal not found", {"goal_id": goal_id})
    if req.progress is not None:
        goal_tracker.update_progress(goal_id, req.progress, req.notes)
    if req.status == "paused":    goal_tracker.pause(goal_id)
    elif req.status == "active":  goal_tracker.resume(goal_id)
    elif req.status == "abandoned": goal_tracker.abandon(goal_id)
    elif req.status == "completed": goal_tracker.complete(goal_id)
    return goal_tracker.get(goal_id)


@router.delete("/goals/{goal_id}", tags=["goals"])
async def delete_goal(goal_id: int):
    from ..loop.goal_tracker import goal_tracker
    goal_tracker.abandon(goal_id)
    return {"status": "abandoned", "goal_id": goal_id}


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions", tags=["sessions"])
async def list_sessions():
    from ..runtime.lifecycle import lifecycle
    return {"sessions": lifecycle.sessions.list_active()}


@router.post("/sessions", tags=["sessions"])
async def create_session(req: SessionCreateReq):
    from ..runtime.lifecycle import lifecycle
    sid = lifecycle.sessions.create(req.name, req.context)
    return {"session_id": sid}


@router.delete("/sessions/{session_id}", tags=["sessions"])
async def end_session(session_id: int):
    from ..runtime.lifecycle import lifecycle
    lifecycle.sessions.end(session_id)
    return {"status": "ended", "session_id": session_id}


# ── Memory ────────────────────────────────────────────────────────────────────

@router.get("/memory/search", tags=["memory"])
async def search_memory(q: str, top_k: int = 5, tags: Optional[str] = None,
                        min_importance: float = 0.0, source: Optional[str] = None):
    from ..memory.store import memory_store
    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    return {"results": memory_store.query(q, top_k=top_k, tags=tag_list or None,
                                           min_importance=min_importance, source=source)}


@router.post("/memory", tags=["memory"])
async def add_memory(req: MemoryAddReq):
    from ..memory.store import memory_store
    mid = memory_store.add(req.content, req.source, req.tags,
                            req.importance, req.metadata)
    return {"memory_id": mid}


@router.get("/memory/recent", tags=["memory"])
async def recent_memory(limit: int = 10):
    from ..memory.store import memory_store
    return {"items": memory_store.get_recent(limit)}


# ── Cron ──────────────────────────────────────────────────────────────────────

@router.get("/cron", tags=["cron"])
async def list_cron():
    from ..runtime.cron import cron_system
    return {"jobs": cron_system.list_jobs()}


@router.post("/cron", tags=["cron"])
async def add_cron(req: CronAddReq):
    from ..runtime.cron import cron_system
    try:
        if req.cron_expr:
            return cron_system.add_cron(req.name, req.cron_expr, req.skill_name,
                                        req.input_data, req.governor_required)
        if req.interval_s:
            return cron_system.add_interval(req.name, req.interval_s, req.skill_name,
                                            req.input_data, req.governor_required)
        raise bad_request("CRON_INPUT_INVALID", "cron_expr or interval_s required")
    except HTTPException:
        raise
    except ValueError as e:
        raise bad_request("CRON_INVALID", str(e), {"name": req.name})
    except Exception as e:
        logger.exception("cron add failed: %s", req.name)
        raise internal_error("CRON_ADD_FAILED", "Failed to add cron job", {"name": req.name, "reason": str(e)})


@router.post("/cron/{name}/trigger", tags=["cron"])
async def trigger_cron(name: str):
    from ..runtime.cron import cron_system
    try:
        return cron_system.trigger_now(name)
    except KeyError as e:
        raise not_found("CRON_NOT_FOUND", str(e), {"name": name})
    except Exception as e:
        logger.exception("cron trigger failed: %s", name)
        raise internal_error("CRON_TRIGGER_FAILED", "Failed to trigger cron job", {"name": name, "reason": str(e)})


@router.delete("/cron/{name}", tags=["cron"])
async def remove_cron(name: str):
    from ..runtime.cron import cron_system
    cron_system.remove(name)
    return {"status": "removed", "name": name}


# ══════════════════════════════════════════════════════════════════════════════
#  LMF — Language Memory Framework  (feature-gated: ENABLE_LMF=true)
# ══════════════════════════════════════════════════════════════════════════════

class LMFEpisodicAddReq(BaseModel):
    event_type: str
    content: str
    source: str = "archillx"
    task_id: Optional[int] = None
    session_id: Optional[int] = None
    importance: float = 0.5
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class LMFSemanticAddReq(BaseModel):
    concept: str
    content: str
    source: str = "archillx"
    confidence: float = 1.0
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class LMFWorkingSetReq(BaseModel):
    task_id: int
    key: str
    value: Any
    ttl_seconds: Optional[int] = None


def _require_lmf():
    from ..config import settings
    if not settings.enable_lmf:
        raise service_unavailable("LMF_DISABLED", "LMF is disabled. Set ENABLE_LMF=true")


@router.post("/lmf/episodic", tags=["lmf"])
async def lmf_add_episodic(req: LMFEpisodicAddReq):
    """Store an episodic memory event."""
    _require_lmf()
    from ..lmf.core.stores import get_episodic_store
    store = get_episodic_store()
    mid = store.add(
        event_type=req.event_type, content=req.content, source=req.source,
        task_id=req.task_id, session_id=req.session_id,
        importance=req.importance, tags=req.tags, metadata=req.metadata,
    )
    return {"memory_id": mid}


@router.get("/lmf/episodic", tags=["lmf"])
async def lmf_search_episodic(q: str = "", event_type: str = "", limit: int = 20):
    """Search episodic memory."""
    _require_lmf()
    from ..lmf.core.stores import get_episodic_store
    store = get_episodic_store()
    results = store.search(q=q, event_type=event_type or None, limit=limit)
    return {"results": results}


@router.post("/lmf/semantic", tags=["lmf"])
async def lmf_add_semantic(req: LMFSemanticAddReq):
    """Store a semantic memory concept."""
    _require_lmf()
    from ..lmf.core.stores import get_semantic_store
    store = get_semantic_store()
    mid = store.upsert(
        concept=req.concept, content=req.content, source=req.source,
        confidence=req.confidence, tags=req.tags, metadata=req.metadata,
    )
    return {"memory_id": mid}


@router.get("/lmf/semantic", tags=["lmf"])
async def lmf_search_semantic(q: str = "", limit: int = 20):
    """Search semantic memory."""
    _require_lmf()
    from ..lmf.core.stores import get_semantic_store
    store = get_semantic_store()
    results = store.search(q=q, limit=limit)
    return {"results": results}


@router.post("/lmf/working", tags=["lmf"])
async def lmf_set_working(req: LMFWorkingSetReq):
    """Set a working memory key for a task."""
    _require_lmf()
    from ..lmf.core.stores import get_working_store
    store = get_working_store()
    store.set(task_id=req.task_id, key=req.key, value=req.value,
              ttl_seconds=req.ttl_seconds)
    return {"status": "ok"}


@router.get("/lmf/working/{task_id}", tags=["lmf"])
async def lmf_get_working(task_id: int):
    """Get all working memory for a task."""
    _require_lmf()
    from ..lmf.core.stores import get_working_store
    store = get_working_store()
    return {"items": store.get_all(task_id)}


@router.delete("/lmf/working/{task_id}", tags=["lmf"])
async def lmf_clear_working(task_id: int):
    """Clear working memory for a task."""
    _require_lmf()
    from ..lmf.core.stores import get_working_store
    store = get_working_store()
    store.clear(task_id)
    return {"status": "cleared", "task_id": task_id}


@router.get("/lmf/procedural", tags=["lmf"])
async def lmf_search_procedural(skill_name: str = "", outcome: str = "", limit: int = 20):
    """Query procedural skill-execution memory."""
    _require_lmf()
    from ..lmf.core.stores import get_procedural_store
    store = get_procedural_store()
    results = store.search(skill_name=skill_name or None,
                           outcome=outcome or None, limit=limit)
    return {"results": results}


@router.get("/lmf/stats", tags=["lmf"])
async def lmf_stats():
    """Return row counts across all LMF tiers."""
    _require_lmf()
    from ..lmf.core.stores import get_lmf_stats
    return {"stats": get_lmf_stats()}


# ══════════════════════════════════════════════════════════════════════════════
#  Planner  (feature-gated: ENABLE_PLANNER=true)
# ══════════════════════════════════════════════════════════════════════════════

class PlannerCreateReq(BaseModel):
    title: str
    goal_id: Optional[int] = None
    session_id: Optional[int] = None
    constraints: dict = Field(default_factory=dict)


def _require_planner():
    from ..config import settings
    if not settings.enable_planner:
        raise service_unavailable("PLANNER_DISABLED", "Planner is disabled. Set ENABLE_PLANNER=true")


@router.post("/planner/plan", tags=["planner"])
async def planner_create(req: PlannerCreateReq):
    """Create and persist a task graph plan."""
    _require_planner()
    from ..planner.taskgraph import task_graph_planner
    result = task_graph_planner.create_plan(
        title=req.title, goal_id=req.goal_id,
        session_id=req.session_id, constraints=req.constraints,
    )
    return result


@router.get("/planner/plans", tags=["planner"])
async def planner_list(status: str = "pending", limit: int = 20):
    """List task graph plans."""
    _require_planner()
    from ..planner.taskgraph import task_graph_planner
    return {"plans": task_graph_planner.list_plans(status=status, limit=limit)}


@router.get("/planner/plans/{plan_id}", tags=["planner"])
async def planner_get(plan_id: int):
    """Get a specific plan by ID."""
    _require_planner()
    from ..planner.taskgraph import task_graph_planner
    plan = task_graph_planner.get_plan(plan_id)
    if not plan:
        raise not_found("PLAN_NOT_FOUND", "Plan not found", {"plan_id": plan_id})
    return plan


@router.post("/planner/plans/{plan_id}/execute", tags=["planner"])
async def planner_execute(plan_id: int):
    """Trigger execution of a plan."""
    _require_planner()
    from ..planner.taskgraph import task_graph_planner
    return task_graph_planner.execute_plan(plan_id)


# ══════════════════════════════════════════════════════════════════════════════
#  Proactive Intelligence  (feature-gated: ENABLE_PROACTIVE=true)
# ══════════════════════════════════════════════════════════════════════════════

class ProjectCreateReq(BaseModel):
    name: str
    goal_statement: str = ""
    metadata: dict = Field(default_factory=dict)


def _require_proactive():
    from ..config import settings
    if not settings.enable_proactive:
        raise service_unavailable("PROACTIVE_DISABLED", "Proactive intelligence is disabled. Set ENABLE_PROACTIVE=true")


@router.get("/proactive/projects", tags=["proactive"])
async def proactive_list_projects():
    """List active proactive intelligence projects."""
    _require_proactive()
    from ..autonomy.proactive import proactive_engine
    return {"projects": proactive_engine.list_projects()}


@router.post("/proactive/projects", tags=["proactive"])
async def proactive_create_project(req: ProjectCreateReq):
    """Register a new project for proactive monitoring."""
    _require_proactive()
    from ..autonomy.proactive import proactive_engine
    pid = proactive_engine.create_project(req.name, req.goal_statement, req.metadata)
    return {"project_id": pid}


@router.post("/proactive/run", tags=["proactive"])
async def proactive_run():
    """Manually trigger one proactive intelligence cycle."""
    _require_proactive()
    from ..autonomy.proactive import proactive_engine
    result = proactive_engine.run_cycle()
    return result


@router.get("/proactive/drivers", tags=["proactive"])
async def proactive_list_drivers(project_id: Optional[int] = None, resolved: bool = False):
    """List daily driver items (BLOCKER / RISK / OPPORTUNITY / …)."""
    _require_proactive()
    from ..autonomy.proactive import proactive_engine
    return {"drivers": proactive_engine.list_drivers(project_id=project_id, resolved=resolved)}


@router.get("/proactive/sprint", tags=["proactive"])
async def proactive_latest_sprint(project_id: Optional[int] = None):
    """Get the latest sprint plan for a project."""
    _require_proactive()
    from ..autonomy.proactive import proactive_engine
    plan = proactive_engine.latest_sprint(project_id)
    if not plan:
        raise not_found("SPRINT_NOT_FOUND", "No sprint plan found")
    return plan


# ══════════════════════════════════════════════════════════════════════════════
#  Notifications  (feature-gated: ENABLE_NOTIFICATIONS=true)
# ══════════════════════════════════════════════════════════════════════════════

class NotifySendReq(BaseModel):
    message: str
    channel: str = "all"        # all | slack | telegram | webhook | websocket
    level: str = "info"         # info | warning | error | success
    metadata: dict = Field(default_factory=dict)


def _require_notifications():
    from ..config import settings
    if not settings.enable_notifications:
        raise service_unavailable("NOTIFICATIONS_DISABLED", "Notifications are disabled. Set ENABLE_NOTIFICATIONS=true")


@router.post("/notifications/send", tags=["notifications"])
async def notifications_send(req: NotifySendReq):
    """Send a notification through one or all configured channels."""
    _require_notifications()
    from ..notifications import dispatch_notification
    result = dispatch_notification(
        message=req.message, channel=req.channel,
        level=req.level, metadata=req.metadata,
    )
    return result


@router.get("/notifications/status", tags=["notifications"])
async def notifications_status():
    """Show which notification channels are configured and active."""
    _require_notifications()
    from ..notifications import get_notification_status
    return get_notification_status()


# ══════════════════════════════════════════════════════════════════════════════
#  Governor / Audit  (always available)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/audit/summary", tags=["governor"])
async def audit_summary(
    decision: Optional[str] = None,
    action: Optional[str] = None,
    action_prefix: Optional[str] = None,
    risk_score_min: Optional[int] = Query(None, ge=0, le=100),
    risk_score_max: Optional[int] = Query(None, ge=0, le=100),
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
):
    """Return aggregate audit stats for current filters."""
    from ..db.schema import SessionLocal, AHAuditLog
    from sqlalchemy import desc

    if risk_score_min is not None and risk_score_max is not None and risk_score_min > risk_score_max:
        raise bad_request(
            "AUDIT_INVALID_RISK_RANGE",
            "risk_score_min cannot be greater than risk_score_max",
            {"risk_score_min": risk_score_min, "risk_score_max": risk_score_max},
        )
    if created_after and created_before and created_after > created_before:
        raise bad_request(
            "AUDIT_INVALID_DATE_RANGE",
            "created_after cannot be later than created_before",
            {
                "created_after": created_after.isoformat(),
                "created_before": created_before.isoformat(),
            },
        )

    db = SessionLocal()
    try:
        q = db.query(AHAuditLog).order_by(desc(AHAuditLog.created_at))
        if decision:
            q = q.filter(AHAuditLog.decision == decision.upper())
        if action:
            q = q.filter(AHAuditLog.action == action)
        if action_prefix:
            q = q.filter(AHAuditLog.action.like(f"{action_prefix}%"))
        if risk_score_min is not None:
            q = q.filter(AHAuditLog.risk_score >= risk_score_min)
        if risk_score_max is not None:
            q = q.filter(AHAuditLog.risk_score <= risk_score_max)
        if created_after:
            q = q.filter(AHAuditLog.created_at >= created_after)
        if created_before:
            q = q.filter(AHAuditLog.created_at <= created_before)
        rows = q.all()

        by_decision: dict[str, int] = {}
        by_action: dict[str, int] = {}
        risk_buckets = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for r in rows:
            d = str(r.decision or "UNKNOWN")
            by_decision[d] = by_decision.get(d, 0) + 1
            a = str(r.action or "unknown")
            by_action[a] = by_action.get(a, 0) + 1
            score = int(r.risk_score or 0)
            if score >= 90:
                risk_buckets["critical"] += 1
            elif score >= 70:
                risk_buckets["high"] += 1
            elif score >= 40:
                risk_buckets["medium"] += 1
            else:
                risk_buckets["low"] += 1

        latest_created_at = rows[0].created_at.isoformat() if rows else None
        return {
            "summary": {
                "total": len(rows),
                "by_decision": by_decision,
                "by_action": by_action,
                "risk_buckets": risk_buckets,
                "latest_created_at": latest_created_at,
            },
            "filters": {
                "decision": decision.upper() if decision else None,
                "action": action,
                "action_prefix": action_prefix,
                "risk_score_min": risk_score_min,
                "risk_score_max": risk_score_max,
                "created_after": created_after.isoformat() if created_after else None,
                "created_before": created_before.isoformat() if created_before else None,
            },
        }
    finally:
        db.close()


@router.get("/audit", tags=["governor"])
async def audit_log(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
    decision: Optional[str] = None,
    action: Optional[str] = None,
    action_prefix: Optional[str] = None,
    risk_score_min: Optional[int] = Query(None, ge=0, le=100),
    risk_score_max: Optional[int] = Query(None, ge=0, le=100),
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
):
    """Query the governor audit log."""
    from ..db.schema import SessionLocal, AHAuditLog
    from sqlalchemy import desc

    if risk_score_min is not None and risk_score_max is not None and risk_score_min > risk_score_max:
        raise bad_request(
            "AUDIT_INVALID_RISK_RANGE",
            "risk_score_min cannot be greater than risk_score_max",
            {"risk_score_min": risk_score_min, "risk_score_max": risk_score_max},
        )
    if created_after and created_before and created_after > created_before:
        raise bad_request(
            "AUDIT_INVALID_DATE_RANGE",
            "created_after cannot be later than created_before",
            {
                "created_after": created_after.isoformat(),
                "created_before": created_before.isoformat(),
            },
        )

    db = SessionLocal()
    try:
        q = db.query(AHAuditLog).order_by(desc(AHAuditLog.created_at))
        if decision:
            q = q.filter(AHAuditLog.decision == decision.upper())
        if action:
            q = q.filter(AHAuditLog.action == action)
        if action_prefix:
            q = q.filter(AHAuditLog.action.like(f"{action_prefix}%"))
        if risk_score_min is not None:
            q = q.filter(AHAuditLog.risk_score >= risk_score_min)
        if risk_score_max is not None:
            q = q.filter(AHAuditLog.risk_score <= risk_score_max)
        if created_after:
            q = q.filter(AHAuditLog.created_at >= created_after)
        if created_before:
            q = q.filter(AHAuditLog.created_at <= created_before)
        rows = q.offset(offset).limit(limit).all()
        return {
            "entries": [
                {
                    "id": r.id, "action": r.action, "decision": r.decision,
                    "risk_score": r.risk_score, "reason": r.reason,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ],
            "filters": {
                "limit": limit,
                "offset": offset,
                "decision": decision.upper() if decision else None,
                "action": action,
                "action_prefix": action_prefix,
                "risk_score_min": risk_score_min,
                "risk_score_max": risk_score_max,
                "created_after": created_after.isoformat() if created_after else None,
                "created_before": created_before.isoformat() if created_before else None,
            },
        }
    finally:
        db.close()


@router.get("/audit/actions", tags=["governor"])
async def audit_actions(
    decision: Optional[str] = None,
    action_prefix: Optional[str] = None,
):
    from ..db.schema import SessionLocal, AHAuditLog
    from sqlalchemy import desc

    db = SessionLocal()
    try:
        q = db.query(AHAuditLog).order_by(desc(AHAuditLog.created_at))
        if decision:
            q = q.filter(AHAuditLog.decision == decision.upper())
        if action_prefix:
            q = q.filter(AHAuditLog.action.like(f"{action_prefix}%"))
        rows = q.all()
        counts: dict[str, int] = {}
        for r in rows:
            a = str(r.action or "unknown")
            counts[a] = counts.get(a, 0) + 1
        return {"actions": [{"action": k, "count": counts[k]} for k in sorted(counts)], "filters": {"decision": decision.upper() if decision else None, "action_prefix": action_prefix}}
    finally:
        db.close()


@router.get("/audit/decisions", tags=["governor"])
async def audit_decisions(action: Optional[str] = None):
    from ..db.schema import SessionLocal, AHAuditLog
    from sqlalchemy import desc

    db = SessionLocal()
    try:
        q = db.query(AHAuditLog).order_by(desc(AHAuditLog.created_at))
        if action:
            q = q.filter(AHAuditLog.action == action)
        rows = q.all()
        counts: dict[str, int] = {}
        for r in rows:
            d = str(r.decision or "UNKNOWN")
            counts[d] = counts.get(d, 0) + 1
        return {"decisions": [{"decision": k, "count": counts[k]} for k in sorted(counts)], "filters": {"action": action}}
    finally:
        db.close()


@router.get("/audit/export", tags=["governor"])
async def audit_export(
    format: str = Query("jsonl", pattern="^(json|jsonl)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    decision: Optional[str] = None,
    action: Optional[str] = None,
    action_prefix: Optional[str] = None,
):
    from ..db.schema import SessionLocal, AHAuditLog
    from sqlalchemy import desc
    import json

    db = SessionLocal()
    try:
        q = db.query(AHAuditLog).order_by(desc(AHAuditLog.created_at))
        if decision:
            q = q.filter(AHAuditLog.decision == decision.upper())
        if action:
            q = q.filter(AHAuditLog.action == action)
        if action_prefix:
            q = q.filter(AHAuditLog.action.like(f"{action_prefix}%"))
        rows = q.offset(offset).limit(limit).all()
        items = []
        for r in rows:
            items.append({
                "id": getattr(r, "id", None),
                "action": r.action,
                "decision": r.decision,
                "risk_score": r.risk_score,
                "reason": getattr(r, "reason", None),
                "context": getattr(r, "context_json", None),
                "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else None,
            })
        if format == "json":
            return {"items": items, "count": len(items), "filters": {"limit": limit, "offset": offset, "decision": decision.upper() if decision else None, "action": action, "action_prefix": action_prefix}}
        body = "\n".join(json.dumps(x, ensure_ascii=False) for x in items)
        return PlainTextResponse(body, media_type="application/x-ndjson")
    finally:
        db.close()


@router.post("/audit/archive", tags=["governor"])
async def audit_archive_roll():
    from ..security.audit_store import archive_snapshot
    return archive_snapshot()


@router.get("/governor/config", tags=["governor"])
async def governor_config():
    """Return current governor configuration."""
    from ..config import settings
    return {
        "mode": settings.governor_mode,
        "risk_block_threshold": settings.risk_block_threshold,
        "risk_warn_threshold": settings.risk_warn_threshold,
        "adaptive": settings.enable_adaptive_governor,
        "consensus": settings.enable_consensus_governor,
        "multi_agent": settings.enable_multi_agent_governor,
    }
