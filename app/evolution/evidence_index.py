from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .proposal_store import _base_dir, _ensure, load_json, latest_json, list_json

EVOLUTION_KINDS = [
    "inspections",
    "plans",
    "proposals",
    "guards",
    "baselines",
    "actions",
    "schedules",
    "dashboards",
]


def _safe_stat(fp: Path) -> dict[str, Any]:
    try:
        st = fp.stat()
        return {
            "filename": fp.name,
            "path": str(fp),
            "size_bytes": st.st_size,
            "modified_at": st.st_mtime,
            "suffix": fp.suffix.lower(),
        }
    except Exception:
        return {"filename": fp.name, "path": str(fp), "size_bytes": 0, "modified_at": None, "suffix": fp.suffix.lower()}


def _extract_identity(kind: str, payload: dict[str, Any], filename: str) -> tuple[str, str | None]:
    key_map = {
        "inspections": "inspection_id",
        "plans": "plan_id",
        "proposals": "proposal_id",
        "guards": "guard_id",
        "baselines": "baseline_id",
        "actions": "action_id",
        "schedules": "cycle_id",
    }
    object_id = str(payload.get(key_map.get(kind, "id")) or Path(filename).stem)
    created_at = payload.get("created_at")
    return object_id, created_at


def _payload_headline(kind: str, payload: dict[str, Any]) -> str:
    if kind == "proposals":
        return str(payload.get("title") or payload.get("summary") or payload.get("source_subject") or "proposal")
    if kind == "plans":
        items = payload.get("items") or []
        return str(items[0].get("title") if items and isinstance(items[0], dict) else "plan")
    if kind == "inspections":
        findings = payload.get("findings") or []
        if findings and isinstance(findings[0], dict):
            return str(findings[0].get("summary") or findings[0].get("subject") or "inspection")
        return str(payload.get("status") or "inspection")
    if kind == "guards":
        return str(payload.get("status") or payload.get("mode") or "guard")
    if kind == "baselines":
        return "regression" if payload.get("regression_detected") else "baseline-clear"
    if kind == "actions":
        return str(payload.get("action") or "action")
    if kind == "schedules":
        return f"cycle proposals={payload.get('proposal_count', 0)}"
    return kind[:-1] if kind.endswith("s") else kind


def list_evidence(kind: str, limit: int = 20) -> list[dict[str, Any]]:
    if kind not in EVOLUTION_KINDS:
        raise ValueError("Unsupported evidence kind.")
    if kind == "dashboards":
        directory = _ensure(kind)
        files = sorted(directory.glob("evolution_summary_*.*"), key=lambda p: p.stat().st_mtime, reverse=True)[: max(1, limit)]
        out: list[dict[str, Any]] = []
        for fp in files:
            meta = _safe_stat(fp)
            out.append({
                "kind": kind,
                "object_id": Path(fp.name).stem,
                "created_at": None,
                "headline": fp.name,
                **meta,
            })
        return out

    directory = _ensure(kind)
    files = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[: max(1, limit)]
    out: list[dict[str, Any]] = []
    for fp in files:
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        object_id, created_at = _extract_identity(kind, payload, fp.name)
        out.append({
            "kind": kind,
            "object_id": object_id,
            "created_at": created_at,
            "headline": _payload_headline(kind, payload),
            **_safe_stat(fp),
        })
    return out


def evidence_index(limit: int = 20) -> dict[str, Any]:
    kinds: dict[str, Any] = {}
    total_items = 0
    for kind in EVOLUTION_KINDS:
        items = list_evidence(kind, limit=limit)
        total_items += len(items)
        kinds[kind] = {
            "count": len(items),
            "latest": items[0] if items else None,
            "items": items,
        }

    latest_proposal = latest_json("proposals") or {}
    latest_guard = latest_json("guards") or {}
    latest_baseline = latest_json("baselines") or {}
    latest_action = latest_json("actions") or {}
    latest_schedule = latest_json("schedules") or {}

    navigation = {}
    if latest_proposal:
        navigation["latest_proposal"] = {
            "proposal_id": latest_proposal.get("proposal_id"),
            "plan_id": latest_proposal.get("plan_id"),
            "inspection_id": latest_proposal.get("inspection_id"),
            "last_guard_id": latest_proposal.get("last_guard_id"),
            "last_baseline_id": latest_proposal.get("last_baseline_id"),
            "status": latest_proposal.get("status"),
            "risk_level": (latest_proposal.get("risk") or {}).get("risk_level"),
        }
    if latest_guard:
        navigation["latest_guard"] = {
            "guard_id": latest_guard.get("guard_id"),
            "proposal_id": latest_guard.get("proposal_id"),
            "status": latest_guard.get("status"),
        }
    if latest_baseline:
        navigation["latest_baseline"] = {
            "baseline_id": latest_baseline.get("baseline_id"),
            "proposal_id": latest_baseline.get("proposal_id"),
            "regression_detected": latest_baseline.get("regression_detected"),
        }
    if latest_action:
        navigation["latest_action"] = {
            "action_id": latest_action.get("action_id"),
            "proposal_id": latest_action.get("proposal_id"),
            "action": latest_action.get("action"),
        }
    if latest_schedule:
        navigation["latest_schedule"] = {
            "cycle_id": latest_schedule.get("cycle_id"),
            "proposal_count": latest_schedule.get("proposal_count"),
        }

    return {
        "base_dir": str(_base_dir()),
        "window_limit": limit,
        "total_items": total_items,
        "kinds": kinds,
        "navigation": navigation,
    }


def proposal_navigation(proposal_id: str) -> dict[str, Any] | None:
    proposal = load_json("proposals", proposal_id)
    if not proposal:
        return None
    inspection_id = proposal.get("inspection_id")
    plan_id = proposal.get("plan_id")
    guard_id = proposal.get("last_guard_id")
    baseline_id = proposal.get("last_baseline_id")
    actions = [x for x in list_json("actions", limit=200) if str(x.get("proposal_id")) == proposal_id]
    dashboards = [x for x in list_evidence("dashboards", limit=50) if proposal_id in x.get("filename", "")]
    return {
        "proposal": proposal,
        "inspection": load_json("inspections", inspection_id) if inspection_id else None,
        "plan": load_json("plans", plan_id) if plan_id else None,
        "guard": load_json("guards", guard_id) if guard_id else None,
        "baseline": load_json("baselines", baseline_id) if baseline_id else None,
        "actions": actions,
        "dashboards": dashboards,
        "links": {
            "inspection_id": inspection_id,
            "plan_id": plan_id,
            "guard_id": guard_id,
            "baseline_id": baseline_id,
            "action_ids": [x.get("action_id") for x in actions],
        },
    }
