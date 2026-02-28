from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .issue_classifier import classify_findings
from .proposal_store import write_json
from .schemas import EvolutionInspectionReport
from .signal_collector import collect_signals


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SelfInspector:
    def run(self) -> EvolutionInspectionReport:
        snapshot = collect_signals()
        findings = classify_findings(snapshot)
        severity_order = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        top = max((severity_order.get(f.severity, 0) for f in findings), default=0)
        status = "critical" if top >= 3 else ("attention" if top >= 1 else "ok")
        report = EvolutionInspectionReport(
            inspection_id=f"insp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}",
            created_at=_now_iso(),
            status=status,
            findings=findings,
            signal_snapshot=snapshot,
        )
        path = write_json("inspections", report.inspection_id, report.model_dump(mode="json"))
        report.evidence_path = path
        return report
