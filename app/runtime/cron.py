"""
ArcHillx v1.0.0 — Cron Scheduling System
APScheduler：cron expression + interval，DB 持久化，Governor 審計前置。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from ..utils.logging_utils import structured_log
from ..utils.telemetry import telemetry

logger = logging.getLogger("archillx.cron")


def _tz() -> str:
    try:
        from ..config import settings
        return settings.cron_timezone
    except Exception:
        return "Asia/Taipei"


class CronSystem:

    def __init__(self):
        self._scheduler = None
        self._started = False

    def startup(self) -> None:
        if self._started:
            return
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            self._scheduler = BackgroundScheduler(timezone=_tz())
            self._scheduler.start()
            self._started = True
            self._restore()
            logger.info("cron system started (tz=%s)", _tz())
        except ImportError:
            logger.warning("apscheduler not installed — cron disabled")
        except Exception as e:
            logger.error("cron startup failed: %s", e)

    def shutdown(self) -> None:
        if self._started and self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
        self._started = False

    # ── Public API ────────────────────────────────────────────────────────────

    def add_cron(self, name: str, cron_expr: str, skill_name: str,
                 input_data: dict | None = None,
                 governor_required: bool = True) -> dict:
        from apscheduler.triggers.cron import CronTrigger
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expr!r}. Need 5 fields.")
        m, h, d, mo, dow = parts
        trigger = CronTrigger(minute=m, hour=h, day=d, month=mo,
                              day_of_week=dow, timezone=_tz())
        return self._add(name, trigger, skill_name, input_data,
                         cron_expr=cron_expr, governor_required=governor_required)

    def add_interval(self, name: str, seconds: int, skill_name: str,
                     input_data: dict | None = None,
                     governor_required: bool = True) -> dict:
        if seconds <= 0:
            raise ValueError("interval seconds must be > 0")
        from apscheduler.triggers.interval import IntervalTrigger
        trigger = IntervalTrigger(seconds=seconds)
        return self._add(name, trigger, skill_name, input_data,
                         interval_s=seconds, governor_required=governor_required)

    def remove(self, name: str) -> None:
        if self._started and self._scheduler:
            try:
                self._scheduler.remove_job(name)
            except Exception:
                pass
        self._set_enabled(name, False)

    def trigger_now(self, name: str) -> dict:
        from ..db.schema import AHCronJob, get_db
        db = next(get_db())
        j = db.query(AHCronJob).filter_by(name=name).first()
        if not j:
            raise KeyError(f"Cron job '{name}' not found.")
        return self._execute(j.skill_name,
                             json.loads(j.input_data or "{}"),
                             j.governor_required)

    def list_jobs(self) -> list[dict]:
        try:
            from ..db.schema import AHCronJob, get_db
            db = next(get_db())
            return [{"id": j.id, "name": j.name, "skill_name": j.skill_name,
                     "cron_expr": j.cron_expr, "interval_s": j.interval_s,
                     "enabled": j.enabled, "run_count": j.run_count,
                     "last_run": j.last_run.isoformat() if j.last_run else None}
                    for j in db.query(AHCronJob).all()]
        except Exception as e:
            logger.warning("cron list_jobs failed: %s", e)
            return []

    # ── Internal ──────────────────────────────────────────────────────────────

    def _add(self, name, trigger, skill_name, input_data,
             cron_expr=None, interval_s=None, governor_required=True) -> dict:
        if not self._started:
            raise RuntimeError("CronSystem not started.")
        self._scheduler.add_job(
            func=self._execute,
            trigger=trigger, id=name, name=name,
            kwargs={"skill_name": skill_name,
                    "input_data": input_data or {},
                    "governor_required": governor_required,
                    "job_name": name},
            replace_existing=True, misfire_grace_time=60,
        )
        self._persist(name, skill_name, cron_expr, interval_s,
                      input_data, governor_required)
        logger.info("cron job added: %s → %s", name, skill_name)
        return {"name": name, "skill_name": skill_name,
                "cron_expr": cron_expr, "interval_s": interval_s}

    def _execute(self, skill_name: str, input_data: dict,
                 governor_required: bool, job_name: str | None = None) -> dict:
        structured_log(logger, logging.INFO, "cron_execute_start", skill_name=skill_name, job_name=job_name or skill_name)
        metric_job = str(job_name or skill_name).replace("-", "_")
        telemetry.incr("cron_execute_total")
        telemetry.incr(f"cron_job_{metric_job}_execute_total")
        try:
            if governor_required:
                from ..governor.governor import governor
                dec = governor.evaluate(
                    f"cron:execute_skill:{skill_name}",
                    {"skill": skill_name, "source": "cron"},
                )
                if dec.decision == "BLOCKED":
                    telemetry.incr("cron_blocked_total")
                    telemetry.incr(f"cron_job_{metric_job}_blocked_total")
                    structured_log(logger, logging.WARNING, "cron_blocked", skill_name=skill_name, job_name=job_name or skill_name, reason=dec.reason)
                    return {"success": False, "error": f"governor_blocked: {dec.reason}"}
            from .skill_manager import skill_manager
            result = skill_manager.invoke(skill_name, input_data, context={"source": "cron", "role": "system"})
            self._bump_run_count(job_name or skill_name)
            if bool(result.get("success", False)):
                telemetry.incr("cron_success_total")
                telemetry.incr(f"cron_job_{metric_job}_success_total")
            else:
                telemetry.incr("cron_failure_total")
                telemetry.incr(f"cron_job_{metric_job}_failure_total")
            structured_log(logger, logging.INFO, "cron_execute_done", skill_name=skill_name, job_name=job_name or skill_name, success=bool(result.get("success", False)))
            return result
        except Exception as e:
            telemetry.incr("cron_failure_total")
            telemetry.incr(f"cron_job_{metric_job}_failure_total")
            structured_log(logger, logging.ERROR, "cron_execute_failed", skill_name=skill_name, job_name=job_name or skill_name, reason=str(e))
            return {"success": False, "error": str(e)}

    def _restore(self) -> None:
        try:
            from ..db.schema import AHCronJob, get_db
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger
            db = next(get_db())
            for j in db.query(AHCronJob).filter_by(enabled=True).all():
                try:
                    if j.cron_expr:
                        p = j.cron_expr.split()
                        trig = CronTrigger(minute=p[0], hour=p[1], day=p[2],
                                           month=p[3], day_of_week=p[4], timezone=_tz())
                    elif j.interval_s:
                        trig = IntervalTrigger(seconds=j.interval_s)
                    else:
                        continue
                    self._scheduler.add_job(
                        func=self._execute, trigger=trig, id=j.name, name=j.name,
                        kwargs={"skill_name": j.skill_name,
                                "input_data": json.loads(j.input_data or "{}"),
                                "governor_required": j.governor_required,
                                "job_name": j.name},
                        replace_existing=True, misfire_grace_time=60,
                    )
                    logger.info("cron restored: %s", j.name)
                except Exception as e:
                    logger.warning("cron restore %s failed: %s", j.name, e)
        except Exception as e:
            logger.warning("cron restore all failed: %s", e)

    def _persist(self, name, skill_name, cron_expr, interval_s,
                 input_data, governor_required) -> None:
        try:
            from ..db.schema import AHCronJob, get_db
            db = next(get_db())
            j = db.query(AHCronJob).filter_by(name=name).first()
            if j:
                j.skill_name = skill_name
                j.cron_expr = cron_expr
                j.interval_s = interval_s
                j.input_data = json.dumps(input_data or {})
                j.governor_required = governor_required
                j.enabled = True
            else:
                db.add(AHCronJob(name=name, skill_name=skill_name,
                                 cron_expr=cron_expr, interval_s=interval_s,
                                 input_data=json.dumps(input_data or {}),
                                 governor_required=governor_required))
            db.commit()
        except Exception as e:
            logger.debug("cron persist failed: %s", e)

    def _set_enabled(self, name: str, enabled: bool) -> None:
        try:
            from ..db.schema import AHCronJob, get_db
            db = next(get_db())
            j = db.query(AHCronJob).filter_by(name=name).first()
            if j:
                j.enabled = enabled
                db.commit()
        except Exception as e:
            logger.debug("cron run_count update failed for %s: %s", job_name, e)

    def _bump_run_count(self, job_name: str) -> None:
        try:
            from ..db.schema import AHCronJob, get_db
            db = next(get_db())
            j = db.query(AHCronJob).filter_by(name=job_name).first()
            if j:
                j.run_count += 1
                j.last_run = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.debug("cron run_count update failed for %s: %s", job_name, e)


cron_system = CronSystem()
