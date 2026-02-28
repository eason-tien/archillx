
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _docs() -> list[dict[str, str]]:
    return [
        {"name": "EVOLUTION_DESIGN", "path": "docs/EVOLUTION_DESIGN.md"},
        {"name": "EVOLUTION_GOVERNANCE", "path": "docs/EVOLUTION_GOVERNANCE.md"},
        {"name": "EVOLUTION_RUNBOOK", "path": "docs/EVOLUTION_RUNBOOK.md"},
        {"name": "EVOLUTION_DASHBOARD", "path": "docs/EVOLUTION_DASHBOARD.md"},
        {"name": "EVOLUTION_EVIDENCE", "path": "docs/EVOLUTION_EVIDENCE.md"},
        {"name": "OPERATIONS_RUNBOOK", "path": "docs/OPERATIONS_RUNBOOK.md"},
    ]


def _api_endpoints() -> list[str]:
    return [
        "/v1/evolution/status",
        "/v1/evolution/report",
        "/v1/evolution/report/run",
        "/v1/evolution/plan",
        "/v1/evolution/plan/run",
        "/v1/evolution/proposals",
        "/v1/evolution/proposals/list",
        "/v1/evolution/proposals/{proposal_id}",
        "/v1/evolution/proposals/generate",
        "/v1/evolution/proposals/{proposal_id}/guard/run",
        "/v1/evolution/proposals/{proposal_id}/baseline/run",
        "/v1/evolution/proposals/{proposal_id}/approve",
        "/v1/evolution/proposals/{proposal_id}/reject",
        "/v1/evolution/proposals/{proposal_id}/apply",
        "/v1/evolution/proposals/{proposal_id}/rollback",
        "/v1/evolution/guard",
        "/v1/evolution/baseline",
        "/v1/evolution/actions",
        "/v1/evolution/actions/list",
        "/v1/evolution/actions/{action_id}",
        "/v1/evolution/schedule",
        "/v1/evolution/schedule/run",
        "/v1/evolution/summary",
        "/v1/evolution/dashboard/render",
        "/v1/evolution/evidence/index",
        "/v1/evolution/evidence/kinds/{kind}",
        "/v1/evolution/evidence/nav/proposals/{proposal_id}",
        "/v1/evolution/subsystem",
        "/v1/evolution/subsystem/render",
    ]


def build_subsystem_manifest(summary: dict[str, Any] | None = None) -> dict[str, Any]:
    base_dir = str((Path(settings.evidence_dir).resolve() / 'evolution'))
    return {
        "generated_at": _now_iso(),
        "name": "evolution",
        "status": "active" if getattr(settings, 'enable_evolution', True) else "disabled",
        "version_tag": "v62",
        "base_dir": base_dir,
        "modules": [
            "signal_collector",
            "self_inspector",
            "issue_classifier",
            "evolution_planner",
            "patch_proposer",
            "upgrade_guard",
            "baseline_compare",
            "auto_scheduler",
            "evidence_index",
            "dashboard_export",
        ],
        "capabilities": [
            "inspection",
            "plan_generation",
            "proposal_generation",
            "guard_validation",
            "baseline_compare",
            "approval_flow",
            "auto_scheduler",
            "summary_api",
            "dashboard_bundle",
            "evidence_navigation",
        ],
        "evidence_kinds": [
            "inspections",
            "plans",
            "proposals",
            "guards",
            "baselines",
            "actions",
            "schedules",
            "dashboards",
        ],
        "api_endpoints": _api_endpoints(),
        "docs": _docs(),
        "recommended_entrypoints": {
            "operator": "/v1/evolution/summary",
            "reviewer": "/v1/evolution/proposals/list",
            "approver": "/v1/evolution/actions/list",
            "evidence": "/v1/evolution/evidence/index",
        },
        "summary": summary or {},
    }
