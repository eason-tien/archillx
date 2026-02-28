from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evolution.service import evolution_service
from app.evolution.proposal_store import write_json

# seed minimal evidence
write_json("inspections", "insp_smoke", {"inspection_id": "insp_smoke", "created_at": "2026-02-27T00:00:00Z", "status": "ok", "findings": [], "signal_snapshot": {"created_at": "x", "readiness": {}, "migration": {}, "telemetry": {}, "audit_summary": {}, "gate_summary": {}}})
write_json("plans", "plan_smoke", {"plan_id": "plan_smoke", "created_at": "2026-02-27T00:00:01Z", "inspection_id": "insp_smoke", "items": []})
write_json("proposals", "prop_smoke", {
    "proposal_id": "prop_smoke", "created_at": "2026-02-27T00:00:02Z", "plan_id": "plan_smoke", "inspection_id": "insp_smoke", "source_subject": "telemetry",
    "title": "refine telemetry", "summary": "...", "suggested_changes": [], "tests_to_add": [], "rollout_notes": [],
    "requires_human_review": False, "risk": {"risk_score": 10, "risk_level": "low", "factors": ["docs"], "auto_apply_allowed": True},
    "status": "generated", "approval_required": False, "last_guard_id": "guard_smoke", "last_baseline_id": "base_smoke"
})
write_json("guards", "guard_smoke", {"guard_id": "guard_smoke", "created_at": "2026-02-27T00:00:03Z", "proposal_id": "prop_smoke", "mode": "quick", "status": "passed", "checks": []})
write_json("baselines", "base_smoke", {"baseline_id": "base_smoke", "created_at": "2026-02-27T00:00:04Z", "proposal_id": "prop_smoke", "inspection_id": "insp_smoke", "before": {"readiness_status": "ok", "migration_status": "head", "http_5xx_total": 0, "skill_failure_total": 0, "sandbox_blocked_total": 0, "governor_blocked_total": 0, "release_failed_total": 0, "rollback_failed_total": 0}, "after": {"readiness_status": "ok", "migration_status": "head", "http_5xx_total": 0, "skill_failure_total": 0, "sandbox_blocked_total": 0, "governor_blocked_total": 0, "release_failed_total": 0, "rollback_failed_total": 0}, "diff": {}, "regression_detected": False, "summary": []})
write_json("actions", "act_smoke", {"action_id": "act_smoke", "created_at": "2026-02-27T00:00:05Z", "proposal_id": "prop_smoke", "action": "approve", "actor": "tester", "from_status": "guard_passed", "to_status": "approved"})
write_json("schedules", "cycle_smoke", {"cycle_id": "cycle_smoke", "created_at": "2026-02-27T00:00:06Z", "proposal_count": 1, "generated_limit": 1})

idx = evolution_service.evidence_index(limit=10)
assert idx["kinds"]["proposals"]["count"] >= 1
nav = evolution_service.proposal_navigation("prop_smoke")
assert nav and nav["guard"]["guard_id"] == "guard_smoke"
assert nav["baseline"]["baseline_id"] == "base_smoke"
print("OK_V61_EVOLUTION_EVIDENCE_SMOKE")
