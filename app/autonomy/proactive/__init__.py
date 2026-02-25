"""
ArcHillx — Proactive Intelligence Engine
=========================================
Autonomously generates daily drivers and weekly sprint plans for registered
projects.  Requires: ENABLE_PROACTIVE=true

Sub-components (individually gated):
  DailyDriver   (ENABLE_DAILY_DRIVER=true)   — BLOCKER / RISK / OPPORTUNITY items
  SprintPlanner (ENABLE_SPRINT_PLANNER=true) — weekly goal/backlog generation

The engine exposes a synchronous `run_cycle()` that can be called:
  - Manually via POST /v1/proactive/run
  - Automatically by the cron system (DAILY_DRIVER_CRON / SPRINT_PLANNER_CRON)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...config import settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  Proactive Engine
# ══════════════════════════════════════════════════════════════════════════════

class ProactiveEngine:
    """
    Central engine for proactive intelligence:
      - project registry
      - driver (BLOCKER/RISK/OPPORTUNITY/DEBT) management
      - sprint plan generation
      - run_cycle() orchestration
    """

    # ── Project management ────────────────────────────────────────────────

    def create_project(
        self,
        name: str,
        goal_statement: str = "",
        metadata: Dict[str, Any] = None,
    ) -> int:
        from ...db.schema import SessionLocal, AHProject
        db = SessionLocal()
        try:
            existing = db.query(AHProject).filter(AHProject.name == name).first()
            if existing:
                return existing.id
            row = AHProject(
                name=name,
                goal_statement=goal_statement,
                status="ACTIVE",
                metadata_=json.dumps(metadata or {}),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            logger.info("[Proactive] Created project '%s' (id=%d)", name, row.id)
            return row.id
        finally:
            db.close()

    def list_projects(self) -> List[Dict[str, Any]]:
        from ...db.schema import SessionLocal, AHProject
        db = SessionLocal()
        try:
            rows = db.query(AHProject).filter(AHProject.status != "FROZEN").all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "goal_statement": r.goal_statement,
                    "status": r.status,
                    "reject_streak": r.reject_streak,
                    "metadata": json.loads(r.metadata_ or "{}"),
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        finally:
            db.close()

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        from ...db.schema import SessionLocal, AHProject
        db = SessionLocal()
        try:
            r = db.query(AHProject).filter(AHProject.id == project_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "name": r.name,
                "goal_statement": r.goal_statement,
                "status": r.status,
                "reject_streak": r.reject_streak,
                "metadata": json.loads(r.metadata_ or "{}"),
                "created_at": r.created_at.isoformat(),
            }
        finally:
            db.close()

    # ── Driver management ─────────────────────────────────────────────────

    def add_driver(
        self,
        *,
        project_id: Optional[int],
        driver_type: str,
        content: str,
        priority: int = 5,
    ) -> int:
        from ...db.schema import SessionLocal, AHDriver
        db = SessionLocal()
        try:
            row = AHDriver(
                project_id=project_id,
                driver_type=driver_type.upper(),
                content=content,
                priority=priority,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row.id
        finally:
            db.close()

    def list_drivers(
        self,
        project_id: Optional[int] = None,
        resolved: bool = False,
    ) -> List[Dict[str, Any]]:
        from ...db.schema import SessionLocal, AHDriver
        db = SessionLocal()
        try:
            query = db.query(AHDriver).filter(AHDriver.resolved == resolved)
            if project_id is not None:
                query = query.filter(AHDriver.project_id == project_id)
            rows = query.order_by(AHDriver.priority.desc()).all()
            return [
                {
                    "id": r.id,
                    "project_id": r.project_id,
                    "driver_type": r.driver_type,
                    "content": r.content,
                    "priority": r.priority,
                    "resolved": r.resolved,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        finally:
            db.close()

    def resolve_driver(self, driver_id: int) -> bool:
        from ...db.schema import SessionLocal, AHDriver
        db = SessionLocal()
        try:
            row = db.query(AHDriver).filter(AHDriver.id == driver_id).first()
            if not row:
                return False
            row.resolved = True
            db.commit()
            return True
        finally:
            db.close()

    # ── Sprint plan management ─────────────────────────────────────────────

    def latest_sprint(self, project_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        from ...db.schema import SessionLocal, AHSprintPlan
        from sqlalchemy import desc
        db = SessionLocal()
        try:
            query = db.query(AHSprintPlan).order_by(desc(AHSprintPlan.week_start))
            if project_id is not None:
                query = query.filter(AHSprintPlan.project_id == project_id)
            row = query.first()
            if not row:
                return None
            return {
                "id": row.id,
                "project_id": row.project_id,
                "week_start": row.week_start.isoformat(),
                "goals": json.loads(row.goals_json or "[]"),
                "backlog": json.loads(row.backlog_json or "[]"),
                "status": row.status,
                "created_at": row.created_at.isoformat(),
            }
        finally:
            db.close()

    def _create_sprint(
        self,
        project_id: Optional[int],
        goals: List[str],
        backlog: List[str],
    ) -> int:
        from ...db.schema import SessionLocal, AHSprintPlan
        db = SessionLocal()
        try:
            row = AHSprintPlan(
                project_id=project_id,
                week_start=datetime.now(timezone.utc).replace(tzinfo=None),
                goals_json=json.dumps(goals),
                backlog_json=json.dumps(backlog),
                status="active",
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row.id
        finally:
            db.close()

    # ── Run cycle ──────────────────────────────────────────────────────────

    def run_cycle(self) -> Dict[str, Any]:
        """
        Execute one proactive intelligence cycle:
          1. For each ACTIVE project, generate daily drivers (if flag enabled)
          2. If sprint day (configurable), generate sprint plan (if flag enabled)

        Returns a summary dict.
        """
        if not settings.enable_proactive:
            return {"status": "disabled", "detail": "ENABLE_PROACTIVE=false"}

        projects = self.list_projects()
        summary: Dict[str, Any] = {
            "cycle_ts": datetime.now(timezone.utc).isoformat(),
            "projects_processed": len(projects),
            "drivers_created": 0,
            "sprints_created": 0,
            "errors": [],
        }

        for project in projects:
            pid = project["id"]
            pname = project["name"]

            # ── Daily Drivers ────────────────────────────────────────────
            if settings.enable_daily_driver:
                try:
                    created = self._generate_drivers(pid, pname, project)
                    summary["drivers_created"] += created
                except Exception as e:
                    logger.error("[Proactive] Driver gen error for '%s': %s", pname, e)
                    summary["errors"].append(f"driver:{pname}:{e}")

            # ── Sprint Planner ───────────────────────────────────────────
            if settings.enable_sprint_planner:
                try:
                    created = self._generate_sprint(pid, pname, project)
                    summary["sprints_created"] += created
                except Exception as e:
                    logger.error("[Proactive] Sprint gen error for '%s': %s", pname, e)
                    summary["errors"].append(f"sprint:{pname}:{e}")

        summary["status"] = "ok" if not summary["errors"] else "partial"
        return summary

    def _generate_drivers(
        self, project_id: int, project_name: str, project: Dict[str, Any]
    ) -> int:
        """
        Generate BLOCKER / RISK / OPPORTUNITY driver items for a project.
        Uses a simple rule-based pass; can be extended with LLM analysis.
        """
        # Check for unresolved BLOCKERs — if none exist, add an OPPORTUNITY as placeholder
        existing = self.list_drivers(project_id=project_id, resolved=False)
        existing_types = {d["driver_type"] for d in existing}

        created = 0
        if "BLOCKER" not in existing_types:
            self.add_driver(
                project_id=project_id,
                driver_type="OPPORTUNITY",
                content=f"[Auto] Review progress for project '{project_name}' and identify next priority.",
                priority=3,
            )
            created += 1
        return created

    def _generate_sprint(
        self, project_id: int, project_name: str, project: Dict[str, Any]
    ) -> int:
        """
        Generate a weekly sprint plan for a project.
        Simple rule-based pass: surfaces top unresolved drivers as sprint goals.
        """
        # Only generate if no active sprint for this week exists
        latest = self.latest_sprint(project_id)
        if latest and latest["status"] == "active":
            return 0

        drivers = self.list_drivers(project_id=project_id, resolved=False)
        top_drivers = sorted(drivers, key=lambda d: -d["priority"])[:5]
        goals = [d["content"] for d in top_drivers if d["driver_type"] in ("BLOCKER", "RISK")]
        backlog = [d["content"] for d in top_drivers if d["driver_type"] not in ("BLOCKER", "RISK")]

        if not goals and not backlog:
            goals = [f"Review and advance project '{project_name}'"]

        self._create_sprint(project_id, goals, backlog)
        return 1


# ── Singleton ──────────────────────────────────────────────────────────────

proactive_engine = ProactiveEngine()
