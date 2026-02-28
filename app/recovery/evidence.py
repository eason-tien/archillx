from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import settings


def _recovery_dir() -> Path:
    base = Path(settings.evidence_dir).resolve() / "recovery"
    base.mkdir(parents=True, exist_ok=True)
    return base


def append_event(event: str, **fields: Any) -> None:
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    out = _recovery_dir() / "recovery.jsonl"
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_snapshot(name: str, content: str) -> str:
    snap = _recovery_dir() / "snapshots"
    snap.mkdir(parents=True, exist_ok=True)
    p = snap / name
    p.write_text(content, encoding="utf-8")
    return str(p)
