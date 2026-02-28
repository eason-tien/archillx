from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .baseline_compare import BaselineCompare
from .dashboard_export import write_dashboard_bundle
from .subsystem_manifest import build_subsystem_manifest
from .navigation_page import write_navigation_bundle
from .portal_index import write_portal_bundle
from .final_bundle import write_final_bundle
from .evidence_index import evidence_index, list_evidence, proposal_navigation
from .evolution_planner import EvolutionPlanner
from .patch_proposer import PatchProposer
from .patch_artifacts import render_patch_artifacts, read_patch_artifact_preview, read_manifest_summary
from .review_export import render_review_export
from .proposal_store import latest_json, load_json, write_json, list_json
from .schemas import (
    EvolutionApprovalAction,
    EvolutionBaselineCompare,
    EvolutionGuardRun,
    EvolutionInspectionReport,
    EvolutionPlan,
    EvolutionProposal,
)
from .self_inspector import SelfInspector
from .upgrade_guard import UpgradeGuard


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvolutionService:
    def __init__(self) -> None:
        self._inspector = SelfInspector()
        self._planner = EvolutionPlanner()
        self._proposer = PatchProposer()
        self._guard = UpgradeGuard()
        self._baseline = BaselineCompare()

    def run_inspection(self) -> EvolutionInspectionReport:
        return self._inspector.run()

    def latest_inspection(self) -> EvolutionInspectionReport | None:
        payload = latest_json("inspections")
        return EvolutionInspectionReport.model_validate(payload) if payload else None

    def build_plan(self, report: EvolutionInspectionReport | None = None) -> EvolutionPlan:
        return self._planner.build(report)

    def latest_plan(self) -> EvolutionPlan | None:
        payload = latest_json("plans")
        return EvolutionPlan.model_validate(payload) if payload else None

    def generate_proposal(self, plan: EvolutionPlan | None = None, item_index: int = 0) -> EvolutionProposal:
        proposal = self._proposer.generate(plan=plan, item_index=item_index)
        proposal.approval_required = proposal.requires_human_review or not proposal.risk.auto_apply_allowed
        path = write_json("proposals", proposal.proposal_id, proposal.model_dump(mode="json"))
        proposal.evidence_path = path
        return proposal

    def latest_proposal(self) -> EvolutionProposal | None:
        payload = latest_json("proposals")
        return EvolutionProposal.model_validate(payload) if payload else None

    def load_proposal(self, proposal_id: str) -> EvolutionProposal | None:
        payload = load_json("proposals", proposal_id)
        return EvolutionProposal.model_validate(payload) if payload else None

    def list_proposals(
        self,
        limit: int = 20,
        *,
        status: str | None = None,
        risk_level: str | None = None,
        subject: str | None = None,
    ) -> list[EvolutionProposal]:
        items = [EvolutionProposal.model_validate(x) for x in list_json("proposals", limit=max(limit * 5, limit))]
        if status:
            want = str(status).strip().lower()
            items = [x for x in items if str(x.status).lower() == want]
        if risk_level:
            want = str(risk_level).strip().lower()
            items = [x for x in items if str(x.risk.risk_level).lower() == want]
        if subject:
            want = str(subject).strip().lower()
            items = [x for x in items if want in str(x.source_subject).lower() or want in str(x.title).lower()]
        return items[: max(1, limit)]

    def save_proposal(self, proposal: EvolutionProposal) -> EvolutionProposal:
        path = write_json("proposals", proposal.proposal_id, proposal.model_dump(mode="json"))
        proposal.evidence_path = path
        return proposal

    def run_guard(self, proposal_id: str | None = None, mode: str = "quick") -> EvolutionGuardRun:
        guard = self._guard.run(proposal_id=proposal_id, mode=mode)
        if proposal_id:
            proposal = self.load_proposal(proposal_id)
            if proposal:
                proposal.last_guard_id = guard.guard_id
                proposal.status = "guard_passed" if guard.status == "passed" else "guard_failed"
                self.save_proposal(proposal)
        return guard


    def proposal_artifact_preview(self, proposal_id: str) -> dict[str, str] | None:
        proposal = self.load_proposal(proposal_id)
        if proposal is None:
            return None
        if not proposal.artifact_paths:
            proposal.artifact_paths = render_patch_artifacts(proposal)
            self.proposal_store.save_json("proposals", proposal.proposal_id, proposal.model_dump(mode="json"))
        return read_patch_artifact_preview(proposal.artifact_paths)

    def proposal_artifact_manifest_summary(self, proposal_id: str) -> dict | None:
        proposal = self.load_proposal(proposal_id)
        if proposal is None:
            return None
        if not proposal.artifact_paths:
            proposal.artifact_paths = render_patch_artifacts(proposal)
            self.proposal_store.save_json("proposals", proposal.proposal_id, proposal.model_dump(mode="json"))
        return read_manifest_summary(proposal.artifact_paths)

    def latest_guard(self) -> EvolutionGuardRun | None:
        payload = latest_json("guards")
        return EvolutionGuardRun.model_validate(payload) if payload else None

    def run_baseline_compare(self, proposal_id: str | None = None) -> EvolutionBaselineCompare:
        baseline = self._baseline.run(proposal_id=proposal_id)
        if proposal_id:
            proposal = self.load_proposal(proposal_id)
            if proposal:
                proposal.last_baseline_id = baseline.baseline_id
                self.save_proposal(proposal)
        return baseline

    def latest_baseline(self) -> EvolutionBaselineCompare | None:
        payload = latest_json("baselines")
        return EvolutionBaselineCompare.model_validate(payload) if payload else None

    def _record_action(self, proposal: EvolutionProposal, action: str, actor: str, reason: str | None, from_status: str, to_status: str) -> EvolutionApprovalAction:
        payload = EvolutionApprovalAction(
            action_id=f"act_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}",
            created_at=_now_iso(),
            proposal_id=proposal.proposal_id,
            action=action,
            actor=actor or "operator",
            reason=reason,
            from_status=from_status,
            to_status=to_status,
        )
        path = write_json("actions", payload.action_id, payload.model_dump(mode="json"))
        payload.evidence_path = path
        return payload

    def _transition(self, proposal_id: str, *, action: str, actor: str, reason: str | None = None) -> tuple[EvolutionProposal, EvolutionApprovalAction]:
        proposal = self.load_proposal(proposal_id)
        if proposal is None:
            raise ValueError("Proposal not found.")
        from_status = proposal.status
        if action == "approve":
            if proposal.status not in {"guard_passed", "generated"}:
                raise ValueError(f"Cannot approve proposal from status {proposal.status}.")
            proposal.status = "approved"
            proposal.approved_by = actor or "operator"
            proposal.approved_at = _now_iso()
        elif action == "reject":
            if proposal.status in {"applied", "rolled_back"}:
                raise ValueError(f"Cannot reject proposal from status {proposal.status}.")
            proposal.status = "rejected"
            proposal.rejected_by = actor or "operator"
            proposal.rejected_at = _now_iso()
        elif action == "apply":
            if proposal.approval_required and proposal.status != "approved":
                raise ValueError("Proposal must be approved before apply.")
            if not proposal.approval_required and proposal.status not in {"generated", "guard_passed", "approved"}:
                raise ValueError(f"Cannot apply proposal from status {proposal.status}.")
            proposal.status = "applied"
            proposal.applied_by = actor or "operator"
            proposal.applied_at = _now_iso()
        elif action == "rollback":
            if proposal.status != "applied":
                raise ValueError("Only applied proposals can be rolled back.")
            proposal.status = "rolled_back"
            proposal.rolled_back_by = actor or "operator"
            proposal.rolled_back_at = _now_iso()
        else:
            raise ValueError("Unsupported action.")
        action_obj = self._record_action(proposal, action, actor, reason, from_status, proposal.status)
        self.save_proposal(proposal)
        return proposal, action_obj

    def approve_proposal(self, proposal_id: str, actor: str, reason: str | None = None):
        return self._transition(proposal_id, action="approve", actor=actor, reason=reason)

    def reject_proposal(self, proposal_id: str, actor: str, reason: str | None = None):
        return self._transition(proposal_id, action="reject", actor=actor, reason=reason)

    def apply_proposal(self, proposal_id: str, actor: str, reason: str | None = None):
        return self._transition(proposal_id, action="apply", actor=actor, reason=reason)

    def rollback_proposal(self, proposal_id: str, actor: str, reason: str | None = None):
        return self._transition(proposal_id, action="rollback", actor=actor, reason=reason)

    def latest_action(self) -> EvolutionApprovalAction | None:
        payload = latest_json("actions")
        return EvolutionApprovalAction.model_validate(payload) if payload else None

    def load_action(self, action_id: str) -> EvolutionApprovalAction | None:
        payload = load_json("actions", action_id)
        return EvolutionApprovalAction.model_validate(payload) if payload else None

    def list_actions(
        self,
        limit: int = 20,
        *,
        action: str | None = None,
        actor: str | None = None,
        proposal_id: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
    ) -> list[EvolutionApprovalAction]:
        items = [EvolutionApprovalAction.model_validate(x) for x in list_json("actions", limit=max(limit * 5, limit))]
        if action:
            want = str(action).strip().lower()
            items = [x for x in items if str(x.action).lower() == want]
        if actor:
            want = str(actor).strip().lower()
            items = [x for x in items if want in str(x.actor).lower()]
        if proposal_id:
            want = str(proposal_id).strip().lower()
            items = [x for x in items if str(x.proposal_id).lower() == want]
        if from_status:
            want = str(from_status).strip().lower()
            items = [x for x in items if str(x.from_status).lower() == want]
        if to_status:
            want = str(to_status).strip().lower()
            items = [x for x in items if str(x.to_status).lower() == want]
        return items[: max(1, limit)]

    def latest_schedule(self) -> dict | None:
        return latest_json("schedules")


    def export_review_section(self, proposal_id: str, section: str) -> dict | None:
        proposal = self.load_proposal(proposal_id)
        if proposal is None:
            return None
        nav = self.proposal_navigation(proposal_id) or {}
        preview = self.proposal_artifact_preview(proposal_id) or {}
        manifest = self.proposal_artifact_manifest_summary(proposal_id) or {}
        summary = {
            "proposal_id": proposal_id,
            "status": proposal.status,
            "risk": proposal.risk.model_dump(mode="json"),
            "last_guard_id": proposal.last_guard_id,
            "last_baseline_id": proposal.last_baseline_id,
        }
        content_map = {
            "guard": nav.get("guard") or {},
            "baseline": nav.get("baseline") or {},
            "artifacts": {"manifest": manifest, "preview": preview, "paths": proposal.artifact_paths},
            "all": {
                "proposal": proposal.model_dump(mode="json"),
                "guard": nav.get("guard") or {},
                "baseline": nav.get("baseline") or {},
                "actions": nav.get("actions") or [],
                "artifacts": {"manifest": manifest, "preview": preview, "paths": proposal.artifact_paths},
            },
        }
        paths = render_review_export(proposal_id, section, summary, content_map[section])
        return {"proposal_id": proposal_id, "section": section, "paths": paths}
    def render_proposal_artifacts(self, proposal_id: str) -> dict[str, str] | None:
        proposal = self.load_proposal(proposal_id)
        if proposal is None:
            return None
        proposal.artifact_paths = render_patch_artifacts(proposal)
        self.save_proposal(proposal)
        return proposal.artifact_paths




    def subsystem_manifest(self, limit: int = 50) -> dict:
        return build_subsystem_manifest(summary=self.summary(limit=limit))

    def render_subsystem_bundle(self, limit: int = 50) -> dict:
        manifest = self.subsystem_manifest(limit=limit)
        ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        base = f"evolution_subsystem_{ts}_{uuid4().hex[:8]}"
        payload = {
            "generated_at": _now_iso(),
            "manifest": manifest,
        }
        json_path = write_json("dashboards", base, payload)
        md = [
            "# Evolution Subsystem Overview",
            "",
            f"Generated at: {payload['generated_at']}",
            "",
            f"Status: {manifest['status']}",
            f"Version tag: {manifest['version_tag']}",
            "",
            "## Capabilities",
        ]
        md.extend([f"- {x}" for x in manifest["capabilities"]])
        md.extend(["", "## Recommended Entrypoints"])
        md.extend([f"- **{k}**: `{v}`" for k, v in manifest["recommended_entrypoints"].items()])
        md.extend(["", "## Evidence Kinds"])
        md.extend([f"- {x}" for x in manifest["evidence_kinds"]])
        md.extend(["", "## Docs"])
        md.extend([f"- {d['name']}: `{d['path']}`" for d in manifest["docs"]])
        md_path = json_path.replace('.json', '.md')
        Path(md_path).write_text('\n'.join(md) + '\n', encoding='utf-8')
        html = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Evolution Subsystem Overview</title>
<style>body{{font-family:Arial,sans-serif;margin:24px;color:#222}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}} .card{{border:1px solid #ddd;border-radius:12px;padding:16px;background:#fafafa}} code{{background:#f3f4f6;padding:2px 6px;border-radius:6px}}</style>
</head><body>
<h1>Evolution Subsystem Overview</h1>
<p><b>Status:</b> {manifest['status']} &nbsp; <b>Version:</b> {manifest['version_tag']}</p>
<div class='grid'>
<div class='card'><h3>Capabilities</h3><ul>{''.join(f'<li>{x}</li>' for x in manifest['capabilities'])}</ul></div>
<div class='card'><h3>Entrypoints</h3><ul>{''.join(f'<li><b>{k}</b>: <code>{v}</code></li>' for k,v in manifest['recommended_entrypoints'].items())}</ul></div>
<div class='card'><h3>Evidence Kinds</h3><ul>{''.join(f'<li>{x}</li>' for x in manifest['evidence_kinds'])}</ul></div>
<div class='card'><h3>Docs</h3><ul>{''.join(f"<li>{d['name']}: <code>{d['path']}</code></li>" for d in manifest['docs'])}</ul></div>
</div>
<h2>Summary Snapshot</h2><pre>{manifest['summary']}</pre>
</body></html>"""
        html_path = json_path.replace('.json', '.html')
        Path(html_path).write_text(html, encoding='utf-8')
        return {"manifest": manifest, "paths": {"json": json_path, "markdown": md_path, "html": html_path}}

    def navigation_page(self, limit: int = 50) -> dict:
        summary = self.summary(limit=limit)
        manifest = self.subsystem_manifest(limit=limit)
        evidence = self.evidence_index(limit=min(limit, 20))
        latest = {
            "inspection_id": (summary.get("latest") or {}).get("inspection_id"),
            "plan_id": (summary.get("latest") or {}).get("plan_id"),
            "proposal_id": (summary.get("latest") or {}).get("proposal_id"),
            "guard_id": (summary.get("latest") or {}).get("guard_id"),
            "baseline_id": (summary.get("latest") or {}).get("baseline_id"),
            "action_id": (summary.get("latest") or {}).get("action_id"),
            "schedule_cycle_id": (summary.get("latest") or {}).get("schedule_cycle_id"),
        }
        bundle_paths = {}
        latest_dash = (evidence.get("kinds", {}).get("dashboards", {}) or {}).get("latest") or {}
        dash_path = latest_dash.get("path")
        if dash_path:
            path = Path(dash_path)
            bundle_paths = {
                "json": str(path.with_suffix('.json')),
                "markdown": str(path.with_suffix('.md')),
                "html": str(path.with_suffix('.html')),
            }
        proposal_id = latest.get("proposal_id")
        nav = self.proposal_navigation(proposal_id) if proposal_id else None
        return {
            "generated_at": _now_iso(),
            "summary": summary,
            "manifest": manifest,
            "docs": manifest.get("docs", []),
            "routes": [
                "/v1/evolution/nav",
                "/v1/evolution/nav/render",
                "/v1/evolution/summary",
                "/v1/evolution/dashboard/render",
                "/v1/evolution/subsystem",
                "/v1/evolution/evidence/index",
                "/v1/evolution/proposals/list",
                "/v1/evolution/actions/list",
            ],
            "latest": latest,
            "bundle_paths": bundle_paths,
            "navigation": (nav or {}).get("links", {}),
            "evidence_index": {
                "total_items": evidence.get("total_items"),
                "base_dir": evidence.get("base_dir"),
            },
        }

    def render_navigation_bundle(self, limit: int = 50) -> dict:
        navigation = self.navigation_page(limit=limit)
        paths = write_navigation_bundle(navigation)
        return {"navigation": navigation, "paths": paths}

    def portal_index(self, limit: int = 50) -> dict:
        navigation = self.navigation_page(limit=limit)
        subsystem = self.subsystem_manifest(limit=limit)
        summary = self.summary(limit=limit)
        blocks = {
            "api_entrypoints": [
                "/v1/evolution/portal",
                "/v1/evolution/portal/render",
                "/v1/evolution/summary",
                "/v1/evolution/nav",
                "/v1/evolution/dashboard/render",
                "/v1/evolution/subsystem",
                "/v1/evolution/evidence/index",
            ],
            "evidence_entrypoints": [
                "/v1/evolution/evidence/index",
                "/v1/evolution/evidence/kinds/proposals",
                "/v1/evolution/evidence/nav/proposals/{proposal_id}",
            ],
            "dashboard_entrypoints": [
                "/v1/evolution/dashboard/render",
                "/v1/evolution/nav/render",
                "/v1/evolution/portal/render",
                "/v1/evolution/subsystem/render",
            ],
            "runbook_entrypoints": subsystem.get("docs", []),
            "recommended_flows": [
                {"label": "Operator review flow", "target": "portal -> summary -> dashboard -> evidence -> runbook"},
                {"label": "Reviewer decision flow", "target": "summary -> proposals/list -> proposal nav -> governance docs"},
                {"label": "Approver / rollback flow", "target": "summary -> actions/list -> runbook -> linked release/rollback/restore"},
            ],
            "latest_navigation": navigation.get("latest", {}),
            "pipeline_snapshot": summary.get("pipeline", {}),
        }
        return {
            "generated_at": _now_iso(),
            "summary": summary,
            "navigation": navigation,
            "subsystem": subsystem,
            "blocks": blocks,
        }

    def render_portal_bundle(self, limit: int = 50) -> dict:
        portal = self.portal_index(limit=limit)
        paths = write_portal_bundle(portal)
        return {"portal": portal, "paths": paths}

    def final_bundle(self, limit: int = 50) -> dict:
        summary = self.summary(limit=limit)
        subsystem = self.subsystem_manifest(limit=limit)
        portal = self.portal_index(limit=limit)
        evidence = self.evidence_index(limit=min(limit, 20))
        docs = [
            {"name": "Evolution Design", "path": "docs/EVOLUTION_DESIGN.md"},
            {"name": "Evolution Governance", "path": "docs/EVOLUTION_GOVERNANCE.md"},
            {"name": "Evolution Runbook", "path": "docs/EVOLUTION_RUNBOOK.md"},
            {"name": "Evolution Dashboard", "path": "docs/EVOLUTION_DASHBOARD.md"},
            {"name": "Evolution Evidence", "path": "docs/EVOLUTION_EVIDENCE.md"},
            {"name": "Evolution Navigation", "path": "docs/EVOLUTION_NAVIGATION.md"},
            {"name": "Evolution Portal", "path": "docs/EVOLUTION_PORTAL.md"},
            {"name": "Evolution Subsystem", "path": "docs/EVOLUTION_SUBSYSTEM.md"},
            {"name": "Evolution Delivery", "path": "docs/EVOLUTION_DELIVERY.md"},
            {"name": "Evolution Delivery Manifest", "path": "docs/EVOLUTION_DELIVERY_MANIFEST.md"},
        ]
        return {
            "generated_at": _now_iso(),
            "status": subsystem.get("status", "ready"),
            "scope": "evolution subsystem final integrated overview",
            "summary": summary,
            "subsystem": subsystem,
            "portal": portal,
            "primary_routes": [
                "/v1/evolution/final",
                "/v1/evolution/final/render",
                "/v1/evolution/summary",
                "/v1/evolution/portal",
                "/v1/evolution/nav",
                "/v1/evolution/evidence/index",
                "/v1/evolution/proposals/list",
                "/v1/evolution/actions/list",
            ],
            "docs": docs,
            "evidence_base_dir": evidence.get("base_dir"),
            "evidence_total_items": evidence.get("total_items"),
            "recommended_flows": portal.get("blocks", {}).get("recommended_flows", []),
        }

    def render_final_bundle(self, limit: int = 50) -> dict:
        bundle = self.final_bundle(limit=limit)
        paths = write_final_bundle(bundle)
        return {"bundle": bundle, "paths": paths}

    def evidence_index(self, limit: int = 20) -> dict:
        return evidence_index(limit=limit)

    def list_evidence(self, kind: str, limit: int = 20) -> list[dict]:
        return list_evidence(kind=kind, limit=limit)

    def proposal_navigation(self, proposal_id: str) -> dict | None:
        return proposal_navigation(proposal_id)

    def summary(self, limit: int = 50) -> dict:
        limit = max(1, min(int(limit or 50), 200))
        inspections = [EvolutionInspectionReport.model_validate(x) for x in list_json("inspections", limit=limit)]
        plans = [EvolutionPlan.model_validate(x) for x in list_json("plans", limit=limit)]
        proposals = [EvolutionProposal.model_validate(x) for x in list_json("proposals", limit=limit)]
        guards = [EvolutionGuardRun.model_validate(x) for x in list_json("guards", limit=limit)]
        baselines = [EvolutionBaselineCompare.model_validate(x) for x in list_json("baselines", limit=limit)]
        actions = [EvolutionApprovalAction.model_validate(x) for x in list_json("actions", limit=limit)]
        schedules = list_json("schedules", limit=limit)

        def _count_by(values):
            out = {}
            for v in values:
                key = str(v)
                out[key] = out.get(key, 0) + 1
            return dict(sorted(out.items()))

        latest_schedule = schedules[0] if schedules else None
        latest_guard = guards[0] if guards else None
        latest_baseline = baselines[0] if baselines else None

        approved_or_applied = sum(1 for p in proposals if p.status in {"approved", "applied", "rolled_back"})
        actionable = sum(1 for p in proposals if p.status in {"generated", "guard_passed", "guard_failed", "approved"})
        pending_approval = sum(1 for p in proposals if p.status in {"generated", "guard_passed"} and p.approval_required)
        auto_apply_candidates = sum(1 for p in proposals if not p.approval_required and p.risk.auto_apply_allowed)
        guard_pass_rate = round((sum(1 for g in guards if g.status == "passed") / len(guards)), 4) if guards else None
        regression_rate = round((sum(1 for b in baselines if b.regression_detected) / len(baselines)), 4) if baselines else None

        return {
            "window_limit": limit,
            "counts": {
                "inspections": len(inspections),
                "plans": len(plans),
                "proposals": len(proposals),
                "guards": len(guards),
                "baselines": len(baselines),
                "actions": len(actions),
                "schedules": len(schedules),
            },
            "proposal_status": _count_by(p.status for p in proposals),
            "proposal_risk": _count_by(p.risk.risk_level for p in proposals),
            "proposal_subjects": _count_by(p.source_subject for p in proposals),
            "action_types": _count_by(a.action for a in actions),
            "action_actors": _count_by(a.actor for a in actions),
            "guard_status": _count_by(g.status for g in guards),
            "baseline_regressions": {
                "detected": sum(1 for b in baselines if b.regression_detected),
                "clear": sum(1 for b in baselines if not b.regression_detected),
            },
            "schedule_overview": {
                "latest_cycle_id": latest_schedule.get("cycle_id") if latest_schedule else None,
                "latest_proposal_count": latest_schedule.get("proposal_count") if latest_schedule else None,
                "latest_generated_limit": latest_schedule.get("generated_limit") if latest_schedule else None,
            },
            "pipeline": {
                "pending_approval": pending_approval,
                "auto_apply_candidates": auto_apply_candidates,
                "actionable": actionable,
                "approved_or_applied": approved_or_applied,
                "guard_pass_rate": guard_pass_rate,
                "regression_rate": regression_rate,
            },
            "latest": {
                "inspection_id": inspections[0].inspection_id if inspections else None,
                "plan_id": plans[0].plan_id if plans else None,
                "proposal_id": proposals[0].proposal_id if proposals else None,
                "guard_id": latest_guard.guard_id if latest_guard else None,
                "baseline_id": latest_baseline.baseline_id if latest_baseline else None,
                "action_id": actions[0].action_id if actions else None,
                "schedule_cycle_id": latest_schedule.get("cycle_id") if latest_schedule else None,
            },
        }

    def render_dashboard_bundle(self, limit: int = 50) -> dict:
        summary = self.summary(limit=limit)
        paths = write_dashboard_bundle(summary)
        return {"summary": summary, "paths": paths}

    def status(self) -> dict:
        inspection = self.latest_inspection()
        plan = self.latest_plan()
        proposal = self.latest_proposal()
        guard = self.latest_guard()
        baseline = self.latest_baseline()
        action = self.latest_action()
        schedule = self.latest_schedule()
        return {
            "inspection": inspection.model_dump(mode="json") if inspection else None,
            "plan": plan.model_dump(mode="json") if plan else None,
            "proposal": proposal.model_dump(mode="json") if proposal else None,
            "guard": guard.model_dump(mode="json") if guard else None,
            "baseline": baseline.model_dump(mode="json") if baseline else None,
            "action": action.model_dump(mode="json") if action else None,
            "schedule": schedule,
        }


evolution_service = EvolutionService()
