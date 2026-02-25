"""
ArcHillx v1.0.0 — Lifecycle Manager
Session / Task / Agent 三層狀態機。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("archillx.lifecycle")


class SessionManager:

    def create(self, name: str, context: dict | None = None) -> int:
        from ..db.schema import AHSession, get_db
        db = next(get_db())
        s = AHSession(name=name, status="active", context=json.dumps(context or {}))
        db.add(s)
        db.commit()
        db.refresh(s)
        logger.info("session created: id=%d", s.id)
        return s.id

    def get(self, sid: int) -> dict | None:
        from ..db.schema import AHSession, get_db
        db = next(get_db())
        s = db.query(AHSession).filter_by(id=sid).first()
        return self._d(s) if s else None

    def pause(self, sid: int, context: dict | None = None) -> None:
        from ..db.schema import AHSession, get_db
        db = next(get_db())
        s = db.query(AHSession).filter_by(id=sid).first()
        if s:
            s.status = "paused"
            if context:
                s.context = json.dumps(context)
            db.commit()

    def resume(self, sid: int) -> dict | None:
        from ..db.schema import AHSession, get_db
        db = next(get_db())
        s = db.query(AHSession).filter_by(id=sid).first()
        if s and s.status == "paused":
            s.status = "active"
            db.commit()
        return self._d(s) if s else None

    def end(self, sid: int) -> None:
        from ..db.schema import AHSession, get_db
        db = next(get_db())
        s = db.query(AHSession).filter_by(id=sid).first()
        if s:
            s.status = "ended"
            db.commit()

    def list_active(self) -> list[dict]:
        from ..db.schema import AHSession, get_db
        db = next(get_db())
        return [self._d(r) for r in db.query(AHSession).filter_by(status="active").all()]

    def _d(self, s: Any) -> dict:
        return {"id": s.id, "name": s.name, "status": s.status,
                "context": json.loads(s.context or "{}"),
                "goal_ids": json.loads(s.goal_ids or "[]"),
                "created_at": s.created_at.isoformat() if s.created_at else None}


class TaskManager:

    def create(self, title: str, task_type: str = "general",
               session_id: int | None = None,
               input_data: dict | None = None) -> int:
        from ..db.schema import AHTask, get_db
        db = next(get_db())
        t = AHTask(title=title[:256], task_type=task_type, session_id=session_id,
                   status="created", input_data=json.dumps(input_data or {}))
        db.add(t)
        db.commit()
        db.refresh(t)
        logger.info("task created: id=%d title=%.60s", t.id, title)
        return t.id

    def assign(self, tid: int, skill: str, governor_ok: bool = True,
               model: str | None = None) -> None:
        self._update(tid, status="assigned", skill_name=skill,
                     governor_ok=governor_ok, model_used=model)

    def start_executing(self, tid: int) -> None:
        self._update(tid, status="executing")

    def start_verifying(self, tid: int) -> None:
        self._update(tid, status="verifying")

    def close(self, tid: int, output: dict | None = None, tokens: int = 0) -> None:
        from ..db.schema import AHTask, get_db
        db = next(get_db())
        t = db.query(AHTask).filter_by(id=tid).first()
        if t:
            t.status = "closed"
            t.output_data = json.dumps(output or {})
            t.tokens_used = tokens
            t.closed_at = datetime.utcnow()
            db.commit()

    def fail(self, tid: int, error: str) -> None:
        from ..db.schema import AHTask, get_db
        db = next(get_db())
        t = db.query(AHTask).filter_by(id=tid).first()
        if t:
            t.status = "failed"
            t.error_msg = error[:2000]
            t.closed_at = datetime.utcnow()
            db.commit()

    def get(self, tid: int) -> dict | None:
        from ..db.schema import AHTask, get_db
        db = next(get_db())
        t = db.query(AHTask).filter_by(id=tid).first()
        return self._d(t) if t else None

    def list_recent(self, limit: int = 20) -> list[dict]:
        from ..db.schema import AHTask, get_db
        db = next(get_db())
        rows = db.query(AHTask).order_by(AHTask.created_at.desc()).limit(limit).all()
        return [self._d(r) for r in rows]

    def _update(self, tid: int, **kwargs) -> None:
        from ..db.schema import AHTask, get_db
        db = next(get_db())
        t = db.query(AHTask).filter_by(id=tid).first()
        if t:
            for k, v in kwargs.items():
                if v is not None:
                    setattr(t, k, v)
            db.commit()

    def _d(self, t: Any) -> dict:
        return {"id": t.id, "title": t.title, "skill_name": t.skill_name,
                "task_type": t.task_type, "status": t.status,
                "governor_ok": t.governor_ok, "model_used": t.model_used,
                "tokens_used": t.tokens_used, "error_msg": t.error_msg,
                "input_data": json.loads(t.input_data or "{}"),
                "output_data": json.loads(t.output_data or "{}"),
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "closed_at": t.closed_at.isoformat() if t.closed_at else None}


class AgentManager:

    def spawn(self, agent_type: str = "general",
              session_id: int | None = None) -> int:
        from ..db.schema import AHAgent, get_db
        db = next(get_db())
        a = AHAgent(agent_type=agent_type, session_id=session_id, status="spawned")
        db.add(a)
        db.commit()
        db.refresh(a)
        logger.info("agent spawned: id=%d type=%s", a.id, agent_type)
        return a.id

    def set_running(self, aid: int, task_id: int | None = None) -> None:
        from ..db.schema import AHAgent, get_db
        db = next(get_db())
        a = db.query(AHAgent).filter_by(id=aid).first()
        if a:
            a.status = "running"
            if task_id:
                a.current_task = task_id
            db.commit()

    def set_idle(self, aid: int) -> None:
        from ..db.schema import AHAgent, get_db
        db = next(get_db())
        a = db.query(AHAgent).filter_by(id=aid).first()
        if a:
            a.status = "idle"
            a.current_task = None
            db.commit()

    def terminate(self, aid: int) -> None:
        from ..db.schema import AHAgent, get_db
        db = next(get_db())
        a = db.query(AHAgent).filter_by(id=aid).first()
        if a:
            a.status = "terminated"
            a.terminated_at = datetime.utcnow()
            db.commit()


class Lifecycle:
    def __init__(self):
        self.sessions = SessionManager()
        self.tasks = TaskManager()
        self.agents = AgentManager()


lifecycle = Lifecycle()
