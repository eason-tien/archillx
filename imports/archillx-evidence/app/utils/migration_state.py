from __future__ import annotations

from pathlib import Path
from typing import Any


def _head_revision() -> str | None:
    versions = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    if not versions.exists():
        return None
    revs: list[str] = []
    for f in versions.glob("*.py"):
        if f.name.startswith("__"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line in text.splitlines():
            if line.strip().startswith("revision") and "=" in line:
                rev = line.split("=", 1)[1].strip().strip("'\"")
                if rev:
                    revs.append(rev)
                    break
    return sorted(revs)[-1] if revs else None


def get_migration_state() -> dict[str, Any]:
    from ..config import settings

    head = _head_revision()
    payload: dict[str, Any] = {
        "enabled": bool(settings.enable_migration_check),
        "required": bool(settings.require_migration_head),
        "head": head,
        "current": None,
        "status": "disabled" if not settings.enable_migration_check else "unknown",
        "ok": not settings.enable_migration_check,
    }

    if not settings.enable_migration_check:
        return payload

    try:
        from ..db.schema import SessionLocal
        from sqlalchemy import text as _sql_text

        db = SessionLocal()
        try:
            row = db.execute(_sql_text("SELECT version_num FROM alembic_version LIMIT 1"))
            if hasattr(row, "scalar"):
                current = row.scalar()
            elif hasattr(row, "fetchone"):
                fetched = row.fetchone()
                current = fetched[0] if fetched else None
            else:
                current = None
        finally:
            db.close()
    except Exception as e:
        payload["error"] = str(e)
        payload["status"] = "unknown"
        payload["ok"] = not settings.require_migration_head
        return payload

    payload["current"] = current
    if head and current == head:
        payload["status"] = "head"
        payload["ok"] = True
    elif current:
        payload["status"] = "behind"
        payload["ok"] = not settings.require_migration_head
    else:
        payload["status"] = "unversioned"
        payload["ok"] = not settings.require_migration_head
    return payload
