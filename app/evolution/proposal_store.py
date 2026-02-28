from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import settings


def _base_dir() -> Path:
    p = Path(settings.evidence_dir).resolve() / "evolution"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ensure(kind: str) -> Path:
    p = _base_dir() / kind
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_json(kind: str, object_id: str, payload: dict[str, Any]) -> str:
    path = _ensure(kind) / f"{object_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return str(path)


def latest_json(kind: str) -> dict[str, Any] | None:
    directory = _ensure(kind)
    files = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    try:
        return json.loads(files[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def load_json(kind: str, object_id: str) -> dict[str, Any] | None:
    path = _ensure(kind) / f"{object_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_json(kind: str, limit: int = 20) -> list[dict[str, Any]]:
    directory = _ensure(kind)
    files = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:max(1, limit)]
    out: list[dict[str, Any]] = []
    for fp in files:
        try:
            out.append(json.loads(fp.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out
