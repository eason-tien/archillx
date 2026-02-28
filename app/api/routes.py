"""
ArcHillx v1.0.0 — API Routes  /v1/*
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


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
    model_used: Optional[str]
    output: Any
    tokens_used: int
    elapsed_s: float
    governor_approved: bool
    error: Optional[str] = None
    memory_hits: list = Field(default_factory=list)


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
        "version": "1.0.0",
        "ai_providers": model_router.list_providers(),
        "loaded_skills": [s["name"] for s in skill_manager.list_skills()],
        "cron_active": cron_system._started,
    }


@router.get("/models", tags=["system"])
async def list_models():
    from ..utils.model_router import model_router
    return {"providers": model_router.list_providers(),
            "available": model_router.available_providers()}


# ── Agent (OODA) ──────────────────────────────────────────────────────────────

@router.post("/agent/run", response_model=AgentRunResp, tags=["agent"])
async def agent_run(req: AgentRunReq):
    """Execute one full OODA cycle: Observe → Orient → Decide → Act → Learn"""
    try:
        from ..loop.main_loop import main_loop, LoopInput
        result = main_loop.run(LoopInput(
            command=req.command, source=req.source,
            session_id=req.session_id, goal_id=req.goal_id,
            context=req.context, skill_hint=req.skill_hint,
            task_type=req.task_type, budget=req.budget,
        ))
        return AgentRunResp(
            success=result.success, task_id=result.task_id,
            skill_used=result.skill_used, model_used=result.model_used,
            output=result.output, tokens_used=result.tokens_used,
            elapsed_s=result.elapsed_s, governor_approved=result.governor_approved,
            error=result.error, memory_hits=result.memory_hits,
        )
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/agent/tasks", tags=["agent"])
async def list_tasks(limit: int = 20):
    from ..runtime.lifecycle import lifecycle
    return {"tasks": lifecycle.tasks.list_recent(limit)}


@router.get("/agent/tasks/{task_id}", tags=["agent"])
async def get_task(task_id: int):
    from ..runtime.lifecycle import lifecycle
    t = lifecycle.tasks.get(task_id)
    if not t:
        raise HTTPException(404, "Task not found")
    return t


# ── Skills ────────────────────────────────────────────────────────────────────

@router.get("/skills", tags=["skills"])
async def list_skills():
    from ..runtime.skill_manager import skill_manager
    return {"skills": skill_manager.list_skills()}


@router.post("/skills/invoke", tags=["skills"])
async def invoke_skill(req: SkillInvokeReq):
    from ..runtime.skill_manager import skill_manager, SkillNotFound
    try:
        return skill_manager.invoke(req.name, req.inputs)
    except SkillNotFound as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


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
        raise HTTPException(404, "Goal not found")
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
async def search_memory(q: str, top_k: int = 5):
    from ..memory.store import memory_store
    return {"results": memory_store.query(q, top_k=top_k)}


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
        elif req.interval_s:
            return cron_system.add_interval(req.name, req.interval_s, req.skill_name,
                                            req.input_data, req.governor_required)
        raise HTTPException(400, "cron_expr or interval_s required")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/cron/{name}/trigger", tags=["cron"])
async def trigger_cron(name: str):
    from ..runtime.cron import cron_system
    try:
        return cron_system.trigger_now(name)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


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
        raise HTTPException(503, "LMF is disabled. Set ENABLE_LMF=true")


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
        raise HTTPException(503, "Planner is disabled. Set ENABLE_PLANNER=true")


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
        raise HTTPException(404, "Plan not found")
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
        raise HTTPException(503, "Proactive intelligence is disabled. Set ENABLE_PROACTIVE=true")


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
        raise HTTPException(404, "No sprint plan found")
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
        raise HTTPException(503, "Notifications are disabled. Set ENABLE_NOTIFICATIONS=true")


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




class EntropyEvalReq(BaseModel):
    indicators: dict = Field(default_factory=dict)
    recent_scores: list[float] = Field(default_factory=list)
    options: dict = Field(default_factory=dict)


class SelfHealingStartReq(BaseModel):
    reason: str = "manual"
    force: bool = False


class SelfHealingTickReq(BaseModel):
    indicators: dict = Field(default_factory=dict)
    recent_scores: list[float] = Field(default_factory=list)
    options: dict = Field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
#  Governor / Audit  (always available)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/audit", tags=["governor"])
async def audit_log(limit: int = 50, decision: Optional[str] = None):
    """Query the governor audit log."""
    from ..db.schema import SessionLocal, AHAuditLog
    from sqlalchemy import desc
    db = SessionLocal()
    try:
        q = db.query(AHAuditLog).order_by(desc(AHAuditLog.created_at))
        if decision:
            q = q.filter(AHAuditLog.decision == decision.upper())
        rows = q.limit(limit).all()
        return {
            "entries": [
                {
                    "id": r.id, "action": r.action, "decision": r.decision,
                    "risk_score": r.risk_score, "reason": r.reason,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        }
    finally:
        db.close()


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


@router.post("/entropy/evaluate", tags=["autonomy"])
async def entropy_evaluate(req: EntropyEvalReq):
    """Evaluate system entropy from normalized instability indicators (0.0 ~ 1.0)."""
    from ..autonomy.entropy_engine import entropy_engine
    return entropy_engine.evaluate(req.indicators, req.recent_scores, req.options)


@router.get("/entropy/sample", tags=["autonomy"])
async def entropy_sample():
    """Return a sample indicator payload for entropy evaluation."""
    return {
        "indicators": {
            "agent_disconnect_rate": 0.2,
            "task_failure_rate": 0.35,
            "latency_p95": 0.5,
            "queue_backlog": 0.4,
            "memory_pressure": 0.3,
            "provider_error_rate": 0.25,
            "governor_block_rate": 0.1,
        },
        "recent_scores": [31.2, 37.8, 45.1],
        "options": {
            "smoothing_alpha": 0.35,
            "high_threshold": 65,
            "critical_threshold": 85,
            "hysteresis": 5,
        },
    }


def _require_self_healing():
    from ..config import settings
    if not settings.enable_self_healing:
        raise HTTPException(503, "Self-healing is disabled. Set ENABLE_SELF_HEALING=true")


@router.post("/self-healing/start", tags=["self-healing"])
async def self_healing_start(req: SelfHealingStartReq):
    """Manually start self-healing takeover."""
    _require_self_healing()
    from ..autonomy.self_healing import self_healing_controller
    return self_healing_controller.start(reason=req.reason, force=req.force)


@router.post("/self-healing/stop", tags=["self-healing"])
async def self_healing_stop(req: SelfHealingStartReq):
    """Manually stop self-healing workflow."""
    _require_self_healing()
    from ..autonomy.self_healing import self_healing_controller
    return self_healing_controller.stop(reason=req.reason)


@router.get("/self-healing/status", tags=["self-healing"])
async def self_healing_status():
    """Get current self-healing controller status."""
    _require_self_healing()
    from ..autonomy.self_healing import self_healing_controller
    return self_healing_controller.status()


@router.get("/self-healing/events", tags=["self-healing"])
async def self_healing_events(limit: int = 50):
    """List latest self-healing events."""
    _require_self_healing()
    from ..autonomy.self_healing import self_healing_controller
    return {"events": self_healing_controller.list_events(limit=limit)}


@router.post("/self-healing/handoff", tags=["self-healing"])
async def self_healing_handoff(req: SelfHealingStartReq):
    """Manually force handoff from self-healing to primary agent."""
    _require_self_healing()
    from ..autonomy.self_healing import self_healing_controller
    return self_healing_controller.handoff(reason=req.reason)


@router.post("/self-healing/tick", tags=["self-healing"])
async def self_healing_tick(req: SelfHealingTickReq):
    """Run one self-healing monitor tick using current indicators."""
    _require_self_healing()
    from ..autonomy.self_healing import self_healing_controller
    return self_healing_controller.tick(
        indicators=req.indicators, options=req.options, recent_scores=req.recent_scores
    )
