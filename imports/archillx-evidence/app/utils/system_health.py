from __future__ import annotations

from typing import Any


def collect_readiness() -> dict[str, Any]:
    checks: dict[str, bool] = {"db": False, "skills": False, "cron": False, "audit_dir": False, "migration": False}
    details: dict[str, Any] = {}
    errors: list[str] = []

    try:
        from ..db.schema import SessionLocal
        db = SessionLocal()
        try:
            from sqlalchemy import text as _sql_text
            db.execute(_sql_text("SELECT 1"))
            checks["db"] = True
            bind = getattr(db, "bind", None)
            details["db"] = {"url": str(getattr(bind, "url", ""))}
        finally:
            db.close()
    except Exception as e:
        errors.append(f"db:{e}")
        details["db"] = {"error": str(e)}

    try:
        from ..runtime.skill_manager import skill_manager
        skills = skill_manager.list_skills()
        checks["skills"] = bool(skills)
        details["skills"] = {"count": len(skills)}
    except Exception as e:
        errors.append(f"skills:{e}")
        details["skills"] = {"error": str(e)}

    try:
        from ..runtime.cron import cron_system
        started = bool(getattr(cron_system, "_started", False))
        checks["cron"] = started
        details["cron"] = {"started": started, "jobs": len(getattr(cron_system, "list_jobs", lambda: [])() or []) if started else 0}
    except Exception as e:
        errors.append(f"cron:{e}")
        details["cron"] = {"error": str(e)}

    try:
        from pathlib import Path
        from ..config import settings
        p = Path(settings.evidence_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        checks["audit_dir"] = p.exists() and p.is_dir()
        details["audit_dir"] = {"path": str(p)}
    except Exception as e:
        errors.append(f"audit_dir:{e}")
        details["audit_dir"] = {"error": str(e)}

    try:
        from ..utils.migration_state import get_migration_state
        mig = get_migration_state()
        checks["migration"] = bool(mig.get("ok", False))
        details["migration"] = mig
        if not mig.get("ok", False):
            errors.append(f"migration:{mig.get('status')}")
    except Exception as e:
        errors.append(f"migration:{e}")
        details["migration"] = {"error": str(e)}

    status = "ready" if all(checks.values()) else "degraded"
    return {"status": status, "checks": checks, "details": details, "errors": errors}
