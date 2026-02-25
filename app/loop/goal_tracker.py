"""
ArcHillx v1.0.0 — Goal Tracker
跨 session 長期目標追蹤，進度 0.0–1.0。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("archillx.goal_tracker")


class GoalTracker:

    def create(self, title: str, description: str = "",
               priority: int = 5, context: dict | None = None) -> int:
        from ..db.schema import AHGoal, get_db
        db = next(get_db())
        g = AHGoal(title=title, description=description, priority=priority,
                   status="active", progress=0.0,
                   context=json.dumps(context or {}))
        db.add(g)
        db.commit()
        db.refresh(g)
        logger.info("goal created: id=%d", g.id)
        return g.id

    def update_progress(self, gid: int, progress: float,
                        notes: str | None = None) -> None:
        from ..db.schema import AHGoal, get_db
        progress = max(0.0, min(1.0, progress))
        db = next(get_db())
        g = db.query(AHGoal).filter_by(id=gid).first()
        if g:
            g.progress = progress
            if progress >= 1.0:
                g.status = "completed"
            if notes:
                ctx = json.loads(g.context or "{}")
                ctx.setdefault("notes", []).append(
                    {"ts": datetime.utcnow().isoformat(), "note": notes})
                g.context = json.dumps(ctx)
            db.commit()

    def pause(self, gid: int) -> None:
        self._status(gid, "paused")

    def resume(self, gid: int) -> None:
        self._status(gid, "active")

    def abandon(self, gid: int) -> None:
        self._status(gid, "abandoned")

    def complete(self, gid: int) -> None:
        from ..db.schema import AHGoal, get_db
        db = next(get_db())
        g = db.query(AHGoal).filter_by(id=gid).first()
        if g:
            g.status = "completed"
            g.progress = 1.0
            db.commit()

    def get(self, gid: int) -> dict | None:
        from ..db.schema import AHGoal, get_db
        db = next(get_db())
        g = db.query(AHGoal).filter_by(id=gid).first()
        return self._d(g) if g else None

    def list_active(self) -> list[dict]:
        from ..db.schema import AHGoal, get_db
        db = next(get_db())
        rows = db.query(AHGoal).filter_by(status="active") \
                               .order_by(AHGoal.priority).all()
        return [self._d(r) for r in rows]

    def list_all(self) -> list[dict]:
        from ..db.schema import AHGoal, get_db
        db = next(get_db())
        rows = db.query(AHGoal).order_by(AHGoal.priority, AHGoal.created_at).all()
        return [self._d(r) for r in rows]

    def sync_to_memory(self, gid: int) -> None:
        g = self.get(gid)
        if not g:
            return
        try:
            from ..memory.store import memory_store
            memory_store.add(
                content=f"[Goal] {g['title']}: progress={g['progress']:.0%} status={g['status']}",
                tags=["goal", f"goal:{gid}"],
                importance=0.7,
                metadata=g,
            )
        except Exception as e:
            logger.debug("sync_to_memory failed: %s", e)

    def _status(self, gid: int, status: str) -> None:
        from ..db.schema import AHGoal, get_db
        db = next(get_db())
        g = db.query(AHGoal).filter_by(id=gid).first()
        if g:
            g.status = status
            db.commit()

    def _d(self, g: Any) -> dict:
        return {"id": g.id, "title": g.title, "description": g.description,
                "status": g.status, "progress": g.progress, "priority": g.priority,
                "context": json.loads(g.context or "{}"),
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "updated_at": g.updated_at.isoformat() if g.updated_at else None}


goal_tracker = GoalTracker()
