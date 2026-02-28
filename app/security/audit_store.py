from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import settings
from ..utils.logging_utils import get_request_context

logger = logging.getLogger("archillx.audit")


DEFAULT_AUDIT_FILE = "security_audit.jsonl"


def _ensure_evidence_dir() -> Path:
    p = Path(settings.evidence_dir).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _archive_dir() -> Path:
    p = _ensure_evidence_dir() / "archive"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except Exception:
        if isinstance(value, dict):
            return {str(k): _json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(v) for v in value]
        return str(value)


def rotate_audit_file(filename: str = DEFAULT_AUDIT_FILE, max_bytes: int | None = None) -> dict[str, Any]:
    max_bytes = int(max_bytes or 0 or getattr(settings, "audit_file_max_bytes", 0) or 0)
    if max_bytes <= 0:
        max_bytes = 5 * 1024 * 1024
    path = _ensure_evidence_dir() / filename
    if not path.exists():
        return {"rotated": False, "path": str(path), "reason": "missing"}
    size = path.stat().st_size
    if size < max_bytes:
        return {"rotated": False, "path": str(path), "size": size, "threshold": max_bytes}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = _archive_dir() / f"{path.stem}.{stamp}{path.suffix}"
    shutil.move(str(path), str(target))
    return {"rotated": True, "path": str(path), "archived_to": str(target), "size": size, "threshold": max_bytes}


def append_jsonl(record: dict[str, Any], filename: str = DEFAULT_AUDIT_FILE) -> str:
    rotate_audit_file(filename=filename)
    path = _ensure_evidence_dir() / filename
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    return str(path)


def load_jsonl_records(filename: str = DEFAULT_AUDIT_FILE) -> list[dict[str, Any]]:
    path = _ensure_evidence_dir() / filename
    if not path.exists():
        return []
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                logger.debug("skip invalid audit line")
    return items


def archive_snapshot() -> dict[str, Any]:
    current = _ensure_evidence_dir() / DEFAULT_AUDIT_FILE
    archived = rotate_audit_file(DEFAULT_AUDIT_FILE, max_bytes=1)
    archived["current_exists"] = current.exists()
    archived["archive_dir"] = str(_archive_dir())
    return archived


def persist_audit(*, action: str, decision: str, risk_score: int = 0, reason: str | None = None,
                  context: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = context.copy() if context else {}
    ctx.setdefault("request_context", get_request_context())
    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "action": str(action),
        "decision": str(decision),
        "risk_score": int(risk_score or 0),
        "reason": reason,
        "context": _json_safe(ctx),
    }
    path = append_jsonl(record)
    record["evidence_path"] = path
    try:
        from ..db.schema import AHAuditLog, get_db
        db = next(get_db())
        db.add(AHAuditLog(
            action=record["action"],
            decision=record["decision"],
            risk_score=record["risk_score"],
            reason=record["reason"],
            context=json.dumps(record["context"], ensure_ascii=False, default=str),
        ))
        db.commit()
    except Exception as e:
        record["db_persisted"] = False
        record["db_error"] = str(e)
        logger.debug("audit db persist skipped: %s", e)
    else:
        record["db_persisted"] = True
    return record
