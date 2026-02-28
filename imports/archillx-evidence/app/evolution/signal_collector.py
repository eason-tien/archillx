from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import settings
from ..security.audit_store import load_jsonl_records
from ..utils.migration_state import get_migration_state
from ..utils.system_health import collect_readiness
from ..utils.telemetry import telemetry
from .schemas import EvolutionSignalSnapshot


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit_summary(limit: int = 200) -> dict[str, Any]:
    records = load_jsonl_records()
    records = records[-limit:]
    by_decision: dict[str, int] = {}
    by_action: dict[str, int] = {}
    for rec in records:
        d = str(rec.get("decision", "UNKNOWN")).upper()
        a = str(rec.get("action", "unknown"))
        by_decision[d] = by_decision.get(d, 0) + 1
        by_action[a] = by_action.get(a, 0) + 1
    latest = records[-1].get("ts") if records else None
    return {
        "total_recent": len(records),
        "by_decision": dict(sorted(by_decision.items())),
        "by_action": dict(sorted(by_action.items())),
        "latest_ts": latest,
    }


def _gate_summary(limit: int = 20) -> dict[str, Any]:
    rel_dir = Path(settings.evidence_dir).resolve() / "releases"
    if not rel_dir.exists():
        return {"total": 0, "release": {}, "rollback": {}}
    files = sorted(rel_dir.glob("*_check_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    release = {"total": 0, "passed": 0, "failed": 0, "latest": None, "updated_at": None}
    rollback = {"total": 0, "passed": 0, "failed": 0, "latest": None, "updated_at": None}
    latest_paths: list[str] = []
    for p in files:
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = p.name
        bucket = release if name.startswith("release_check_") else rollback
        bucket["total"] += 1
        ok = bool(payload.get("ok", payload.get("status") in ("ok", "passed")))
        bucket["passed" if ok else "failed"] += 1
        if bucket.get("latest") is None:
            bucket["latest"] = str(p)
            try:
                bucket["updated_at"] = datetime.utcfromtimestamp(p.stat().st_mtime).isoformat() + "Z"
            except Exception:
                bucket["updated_at"] = None
        latest_paths.append(str(p))
    return {
        "total": len(latest_paths),
        "release": release,
        "rollback": rollback,
        "latest_paths": latest_paths[:5],
    }


def collect_signals() -> EvolutionSignalSnapshot:
    return EvolutionSignalSnapshot(
        created_at=_now_iso(),
        readiness=collect_readiness(),
        migration=get_migration_state(),
        telemetry={
            "aggregate": telemetry.aggregated_snapshot(),
            "history": telemetry.history_snapshot(),
        },
        audit_summary=_audit_summary(),
        gate_summary=_gate_summary(),
    )
