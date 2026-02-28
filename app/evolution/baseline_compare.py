from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .proposal_store import latest_json, load_json, write_json
from .schemas import EvolutionBaselineCompare, EvolutionBaselinePoint, EvolutionInspectionReport, EvolutionProposal
from .signal_collector import collect_signals


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _point_from_snapshot(snapshot) -> EvolutionBaselinePoint:
    agg = (snapshot.telemetry or {}).get("aggregate", {}) if hasattr(snapshot, 'telemetry') else {}
    audit = snapshot.audit_summary if hasattr(snapshot, 'audit_summary') else {}
    gate = snapshot.gate_summary if hasattr(snapshot, 'gate_summary') else {}
    http = agg.get("http", {})
    skills = agg.get("skills", {}).get("totals", {})
    gov = agg.get("governor", {})
    sandbox = agg.get("sandbox", {})
    return EvolutionBaselinePoint(
        readiness_status=str((snapshot.readiness or {}).get("status", "unknown")),
        migration_status=str((snapshot.migration or {}).get("status", "unknown")),
        http_5xx_total=int(((http.get("status", {}) or {}).get("5xx", 0)) or 0),
        skill_failure_total=int(skills.get("failure_total", 0) or 0),
        sandbox_blocked_total=int(((sandbox.get("decision", {}) or {}).get("BLOCKED", 0)) or 0),
        governor_blocked_total=int(((gov.get("decisions", {}) or {}).get("blocked", 0)) or 0),
        release_failed_total=int((((gate.get("release", {}) or {}).get("failed", 0)) or 0)),
        rollback_failed_total=int((((gate.get("rollback", {}) or {}).get("failed", 0)) or 0)),
    )


class BaselineCompare:
    def _load_proposal(self, proposal_id: str | None = None) -> EvolutionProposal:
        payload = load_json("proposals", proposal_id) if proposal_id else latest_json("proposals")
        if payload is None:
            raise ValueError("No evolution proposal available for baseline comparison.")
        return EvolutionProposal.model_validate(payload)

    def _load_inspection(self, inspection_id: str | None) -> EvolutionInspectionReport:
        if inspection_id:
            payload = load_json("inspections", inspection_id)
            if payload is not None:
                return EvolutionInspectionReport.model_validate(payload)
        latest = latest_json("inspections")
        if latest is None:
            from .self_inspector import SelfInspector
            return SelfInspector().run()
        return EvolutionInspectionReport.model_validate(latest)

    def run(self, proposal_id: str | None = None) -> EvolutionBaselineCompare:
        proposal = self._load_proposal(proposal_id)
        inspection = self._load_inspection(proposal.inspection_id)
        current = collect_signals()

        before = _point_from_snapshot(inspection.signal_snapshot)
        after = _point_from_snapshot(current)
        diff = {
            "readiness_status": f"{before.readiness_status}->{after.readiness_status}",
            "migration_status": f"{before.migration_status}->{after.migration_status}",
            "http_5xx_total": after.http_5xx_total - before.http_5xx_total,
            "skill_failure_total": after.skill_failure_total - before.skill_failure_total,
            "sandbox_blocked_total": after.sandbox_blocked_total - before.sandbox_blocked_total,
            "governor_blocked_total": after.governor_blocked_total - before.governor_blocked_total,
            "release_failed_total": after.release_failed_total - before.release_failed_total,
            "rollback_failed_total": after.rollback_failed_total - before.rollback_failed_total,
        }

        regressions = []
        if before.readiness_status == "ok" and after.readiness_status != "ok":
            regressions.append("readiness degraded")
        if before.migration_status == "head" and after.migration_status != "head":
            regressions.append("migration drift detected")
        if diff["http_5xx_total"] > 0:
            regressions.append("http 5xx increased")
        if diff["skill_failure_total"] > 0:
            regressions.append("skill failures increased")
        if diff["sandbox_blocked_total"] > 0:
            regressions.append("sandbox blocked events increased")
        if diff["governor_blocked_total"] > 0:
            regressions.append("governor blocked decisions increased")
        if diff["release_failed_total"] > 0 or diff["rollback_failed_total"] > 0:
            regressions.append("gate failures increased")

        compare = EvolutionBaselineCompare(
            baseline_id=f"base_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}",
            created_at=_now_iso(),
            proposal_id=proposal.proposal_id,
            inspection_id=inspection.inspection_id,
            before=before,
            after=after,
            diff=diff,
            regression_detected=bool(regressions),
            summary=regressions or ["no regression detected"],
        )
        path = write_json("baselines", compare.baseline_id, compare.model_dump(mode="json"))
        compare.evidence_path = path
        return compare
