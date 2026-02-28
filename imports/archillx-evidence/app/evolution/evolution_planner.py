from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .proposal_store import latest_json, write_json
from .schemas import EvolutionFinding, EvolutionInspectionReport, EvolutionPlan, EvolutionPlanItem


_SCOPE_MAP = {
    "readiness": ["app/utils/system_health.py", "tests/test_api_system_routes.py"],
    "migration": ["app/utils/migration_state.py", "tests/test_api_production_routes.py"],
    "http": ["app/main.py", "app/utils/telemetry.py", "tests/test_api_routes.py"],
    "skills": ["app/runtime/skill_manager.py", "tests/test_api_security_integration.py"],
    "sandbox": ["app/security/sandbox_policy.py", "app/skills/code_exec.py", "tests/test_code_exec_security.py"],
    "audit": ["app/security/audit_store.py", "tests/test_api_audit_summary_routes.py"],
    "release_gate": ["scripts/release_check.py", "scripts/rollback_check.py", "scripts/smoke_test_v37_release_check.py"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _priority_for(finding: EvolutionFinding) -> str:
    if finding.severity == "critical":
        return "P0"
    if finding.severity == "high":
        return "P1"
    return "P2"


def _benefit_for(finding: EvolutionFinding) -> str:
    return {
        "security": "reduce security exposure and false-negative risk",
        "stability": "improve runtime stability and reduce incident frequency",
        "reliability": "reduce repeated failures and improve success rate",
        "operability": "restore operator confidence and deployment readiness",
        "deployment_gap": "improve upgrade confidence and reduce rollout risk",
        "migration_gap": "prevent schema drift and failed deployments",
    }.get(finding.category, "improve system maintainability")


class EvolutionPlanner:
    def build(self, report: EvolutionInspectionReport | None = None) -> EvolutionPlan:
        if report is None:
            latest = latest_json("inspections")
            if latest is None:
                from .self_inspector import SelfInspector
                report = SelfInspector().run()
            else:
                report = EvolutionInspectionReport.model_validate(latest)
        items: list[EvolutionPlanItem] = []
        for finding in report.findings:
            items.append(EvolutionPlanItem(
                priority=_priority_for(finding),
                category=finding.category,
                title=f"Investigate {finding.subject}: {finding.summary}",
                subject=finding.subject,
                expected_benefit=_benefit_for(finding),
                suggested_scope=_SCOPE_MAP.get(finding.subject, ["docs/OPERATIONS_RUNBOOK.md"]),
                requires_human_review=finding.requires_human_review,
                source_inspection_id=report.inspection_id,
            ))
        plan = EvolutionPlan(
            plan_id=f"plan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}",
            created_at=_now_iso(),
            inspection_id=report.inspection_id,
            items=items,
        )
        path = write_json("plans", plan.plan_id, plan.model_dump(mode="json"))
        plan.evidence_path = path
        return plan
