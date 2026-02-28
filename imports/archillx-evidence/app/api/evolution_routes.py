from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..evolution.service import evolution_service
from ..evolution.auto_scheduler import evolution_scheduler
from ..utils.api_errors import bad_request, service_unavailable, not_found
from ..config import settings

router = APIRouter(tags=["evolution"])


class ProposalGenerateReq(BaseModel):
    item_index: int = Field(default=0, ge=0)


class GuardRunReq(BaseModel):
    mode: str = Field(default="quick")


class ProposalActionReq(BaseModel):
    actor: str = Field(default="operator", min_length=1)
    reason: str | None = None


class EvolutionScheduleRunReq(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=20)


class ProposalListReq(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    status: str | None = None
    risk_level: str | None = None
    subject: str | None = None


class EvolutionSummaryReq(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)


def _require_enabled() -> None:
    if not getattr(settings, "enable_evolution", True):
        raise service_unavailable("EVOLUTION_DISABLED", "Evolution module is disabled. Set ENABLE_EVOLUTION=true")




@router.get("/evolution/final")
async def get_evolution_final(limit: int = 50):
    _require_enabled()
    return evolution_service.final_bundle(limit=limit)

@router.get("/evolution/final/preview", response_class=HTMLResponse)
async def preview_evolution_final(limit: int = 50):
    _require_enabled()
    bundle = evolution_service.render_final_bundle(limit=limit)
    html_path = (bundle.get("paths") or {}).get("html") or bundle.get("html")
    if not html_path:
        raise service_unavailable("EVOLUTION_FINAL_PREVIEW_UNAVAILABLE", "Final HTML preview is unavailable.")
    from pathlib import Path
    return HTMLResponse(Path(html_path).read_text(encoding="utf-8"))


@router.post("/evolution/final/render")
async def render_evolution_final(limit: int = 50):
    _require_enabled()
    return evolution_service.render_final_bundle(limit=limit)


@router.get("/evolution/portal")
async def get_evolution_portal(limit: int = 50):
    _require_enabled()
    return evolution_service.portal_index(limit=limit)

@router.get("/evolution/portal/preview", response_class=HTMLResponse)
async def preview_evolution_portal(limit: int = 50):
    _require_enabled()
    bundle = evolution_service.render_portal_bundle(limit=limit)
    html_path = (bundle.get("paths") or {}).get("html") or bundle.get("html")
    if not html_path:
        raise service_unavailable("EVOLUTION_PORTAL_PREVIEW_UNAVAILABLE", "Portal HTML preview is unavailable.")
    from pathlib import Path
    return HTMLResponse(Path(html_path).read_text(encoding="utf-8"))


@router.post("/evolution/portal/render")
async def render_evolution_portal(limit: int = 50):
    _require_enabled()
    return evolution_service.render_portal_bundle(limit=limit)


@router.get("/evolution/nav")
@router.get("/evolution/navigation")
async def get_evolution_navigation(limit: int = 50):
    _require_enabled()
    return evolution_service.navigation_page(limit=limit)


@router.post("/evolution/nav/render")
@router.post("/evolution/navigation/render")
async def render_evolution_navigation(limit: int = 50):
    _require_enabled()
    return evolution_service.render_navigation_bundle(limit=limit)


@router.get("/evolution/subsystem")
async def get_evolution_subsystem(limit: int = 50):
    _require_enabled()
    return evolution_service.subsystem_manifest(limit=limit)


@router.post("/evolution/subsystem/render")
async def render_evolution_subsystem(limit: int = 50):
    _require_enabled()
    return evolution_service.render_subsystem_bundle(limit=limit)


@router.get("/evolution/summary")
async def get_evolution_summary(limit: int = 50):
    _require_enabled()
    return evolution_service.summary(limit=limit)


@router.post("/evolution/dashboard/render")
async def render_evolution_dashboard(limit: int = 50):
    _require_enabled()
    return evolution_service.render_dashboard_bundle(limit=limit)

@router.get("/evolution/evidence/index")
async def get_evolution_evidence_index(limit: int = 20):
    _require_enabled()
    return evolution_service.evidence_index(limit=limit)


@router.get("/evolution/evidence/kinds/{kind}")
async def list_evolution_evidence_kind(kind: str, limit: int = 20):
    _require_enabled()
    try:
        items = evolution_service.list_evidence(kind=kind, limit=limit)
        return {"kind": kind, "items": items, "limit": limit}
    except ValueError as e:
        raise bad_request("EVOLUTION_EVIDENCE_KIND_INVALID", str(e))


@router.get("/evolution/evidence/nav/proposals/{proposal_id}")
async def get_evolution_proposal_navigation(proposal_id: str):
    _require_enabled()
    payload = evolution_service.proposal_navigation(proposal_id)
    if payload is None:
        raise not_found("EVOLUTION_PROPOSAL_NOT_FOUND", "Proposal not found.")
    return payload


@router.get("/evolution/status")
async def evolution_status():
    _require_enabled()
    return evolution_service.status()


@router.get("/evolution/report")
async def get_evolution_report():
    _require_enabled()
    report = evolution_service.latest_inspection()
    if report is None:
        report = evolution_service.run_inspection()
    return report.model_dump(mode="json")


@router.post("/evolution/report/run")
async def run_evolution_report():
    _require_enabled()
    report = evolution_service.run_inspection()
    return report.model_dump(mode="json")


@router.get("/evolution/plan")
async def get_evolution_plan():
    _require_enabled()
    plan = evolution_service.latest_plan()
    if plan is None:
        inspection = evolution_service.latest_inspection() or evolution_service.run_inspection()
        plan = evolution_service.build_plan(inspection)
    return plan.model_dump(mode="json")


@router.post("/evolution/plan/run")
async def run_evolution_plan():
    _require_enabled()
    inspection = evolution_service.latest_inspection() or evolution_service.run_inspection()
    plan = evolution_service.build_plan(inspection)
    return plan.model_dump(mode="json")


@router.get("/evolution/proposals")
async def get_latest_evolution_proposal():
    _require_enabled()
    proposal = evolution_service.latest_proposal()
    if proposal is None:
        plan = evolution_service.latest_plan()
        if plan is None:
            inspection = evolution_service.latest_inspection() or evolution_service.run_inspection()
            plan = evolution_service.build_plan(inspection)
        proposal = evolution_service.generate_proposal(plan=plan, item_index=0)
    return proposal.model_dump(mode="json")




@router.get("/evolution/proposals/list")
async def list_evolution_proposals(limit: int = 20, status: str | None = None, risk_level: str | None = None, subject: str | None = None):
    _require_enabled()
    items = evolution_service.list_proposals(limit=limit, status=status, risk_level=risk_level, subject=subject)
    return {
        "items": [x.model_dump(mode="json") for x in items],
        "filters": {"limit": limit, "status": status, "risk_level": risk_level, "subject": subject},
    }


@router.get("/evolution/proposals/{proposal_id}")
async def get_evolution_proposal(proposal_id: str):
    _require_enabled()
    proposal = evolution_service.load_proposal(proposal_id)
    if proposal is None:
        raise not_found("EVOLUTION_PROPOSAL_NOT_FOUND", "Proposal not found.")
    return proposal.model_dump(mode="json")


@router.get("/evolution/proposals/{proposal_id}/artifacts")
async def get_evolution_proposal_artifacts(proposal_id: str):
    _require_enabled()
    proposal = evolution_service.load_proposal(proposal_id)
    if proposal is None:
        raise not_found("EVOLUTION_PROPOSAL_NOT_FOUND", "Proposal not found.")
    if not proposal.artifact_paths:
        proposal.artifact_paths = evolution_service.render_proposal_artifacts(proposal_id) or {}
    return {"proposal_id": proposal_id, "artifacts": proposal.artifact_paths}




@router.get("/evolution/proposals/{proposal_id}/artifacts/manifest")
async def get_evolution_proposal_artifact_manifest(proposal_id: str):
    _require_enabled()
    payload = evolution_service.proposal_artifact_manifest_summary(proposal_id)
    if payload is None:
        raise not_found("EVOLUTION_PROPOSAL_NOT_FOUND", "Proposal not found.")
    return {"proposal_id": proposal_id, "manifest": payload}

@router.get("/evolution/proposals/{proposal_id}/artifacts/preview")
async def preview_evolution_proposal_artifacts(proposal_id: str):
    _require_enabled()
    preview = evolution_service.proposal_artifact_preview(proposal_id)
    if preview is None:
        raise not_found("EVOLUTION_PROPOSAL_NOT_FOUND", "Proposal not found.")
    return {"proposal_id": proposal_id, "preview": preview}


@router.post("/evolution/proposals/{proposal_id}/artifacts/render")
async def render_evolution_proposal_artifacts(proposal_id: str):
    _require_enabled()
    artifacts = evolution_service.render_proposal_artifacts(proposal_id)
    if artifacts is None:
        raise not_found("EVOLUTION_PROPOSAL_NOT_FOUND", "Proposal not found.")
    return {"proposal_id": proposal_id, "artifacts": artifacts}




@router.post("/evolution/proposals/{proposal_id}/review/export")
async def export_evolution_proposal_review(proposal_id: str, section: str = "all"):
    _require_enabled()
    try:
        payload = evolution_service.export_review_section(proposal_id, section)
    except ValueError as e:
        raise bad_request("EVOLUTION_REVIEW_EXPORT_INVALID_SECTION", str(e))
    if payload is None:
        raise not_found("EVOLUTION_PROPOSAL_NOT_FOUND", "Proposal not found.")
    return payload

@router.post("/evolution/proposals/generate")
async def generate_evolution_proposal(req: ProposalGenerateReq):
    _require_enabled()
    plan = evolution_service.latest_plan()
    if plan is None:
        inspection = evolution_service.latest_inspection() or evolution_service.run_inspection()
        plan = evolution_service.build_plan(inspection)
    proposal = evolution_service.generate_proposal(plan=plan, item_index=req.item_index)
    return proposal.model_dump(mode="json")


@router.get("/evolution/guard")
async def get_latest_evolution_guard():
    _require_enabled()
    guard = evolution_service.latest_guard()
    if guard is None:
        proposal = evolution_service.latest_proposal()
        if proposal is None:
            plan = evolution_service.latest_plan()
            if plan is None:
                inspection = evolution_service.latest_inspection() or evolution_service.run_inspection()
                plan = evolution_service.build_plan(inspection)
            proposal = evolution_service.generate_proposal(plan=plan, item_index=0)
        guard = evolution_service.run_guard(proposal_id=proposal.proposal_id, mode="quick")
    return guard.model_dump(mode="json")


@router.post("/evolution/proposals/{proposal_id}/guard/run")
async def run_evolution_guard(proposal_id: str, req: GuardRunReq):
    _require_enabled()
    guard = evolution_service.run_guard(proposal_id=proposal_id, mode=req.mode)
    return guard.model_dump(mode="json")


@router.get("/evolution/baseline")
async def get_latest_evolution_baseline():
    _require_enabled()
    baseline = evolution_service.latest_baseline()
    if baseline is None:
        proposal = evolution_service.latest_proposal()
        if proposal is None:
            plan = evolution_service.latest_plan()
            if plan is None:
                inspection = evolution_service.latest_inspection() or evolution_service.run_inspection()
                plan = evolution_service.build_plan(inspection)
            proposal = evolution_service.generate_proposal(plan=plan, item_index=0)
        baseline = evolution_service.run_baseline_compare(proposal_id=proposal.proposal_id)
    return baseline.model_dump(mode="json")


@router.post("/evolution/proposals/{proposal_id}/baseline/run")
async def run_evolution_baseline(proposal_id: str):
    _require_enabled()
    baseline = evolution_service.run_baseline_compare(proposal_id=proposal_id)
    return baseline.model_dump(mode="json")


@router.get("/evolution/actions")
async def list_evolution_actions(limit: int = 20):
    _require_enabled()
    return [x.model_dump(mode="json") for x in evolution_service.list_actions(limit=limit)]


@router.get("/evolution/actions/list")
async def list_evolution_actions_filtered(
    limit: int = 20,
    action: str | None = None,
    actor: str | None = None,
    proposal_id: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
):
    _require_enabled()
    items = evolution_service.list_actions(
        limit=limit,
        action=action,
        actor=actor,
        proposal_id=proposal_id,
        from_status=from_status,
        to_status=to_status,
    )
    return {
        "items": [x.model_dump(mode="json") for x in items],
        "filters": {
            "limit": limit,
            "action": action,
            "actor": actor,
            "proposal_id": proposal_id,
            "from_status": from_status,
            "to_status": to_status,
        },
    }


@router.get("/evolution/actions/{action_id}")
async def get_evolution_action(action_id: str):
    _require_enabled()
    action_obj = evolution_service.load_action(action_id)
    if action_obj is None:
        raise not_found("EVOLUTION_ACTION_NOT_FOUND", "Evolution action not found.")
    return action_obj.model_dump(mode="json")


@router.post("/evolution/proposals/{proposal_id}/approve")
async def approve_evolution_proposal(proposal_id: str, req: ProposalActionReq):
    _require_enabled()
    try:
        proposal, action = evolution_service.approve_proposal(proposal_id, actor=req.actor, reason=req.reason)
        return {"proposal": proposal.model_dump(mode="json"), "action": action.model_dump(mode="json")}
    except ValueError as e:
        raise bad_request("EVOLUTION_INVALID_TRANSITION", str(e))


@router.post("/evolution/proposals/{proposal_id}/reject")
async def reject_evolution_proposal(proposal_id: str, req: ProposalActionReq):
    _require_enabled()
    try:
        proposal, action = evolution_service.reject_proposal(proposal_id, actor=req.actor, reason=req.reason)
        return {"proposal": proposal.model_dump(mode="json"), "action": action.model_dump(mode="json")}
    except ValueError as e:
        raise bad_request("EVOLUTION_INVALID_TRANSITION", str(e))


@router.post("/evolution/proposals/{proposal_id}/apply")
async def apply_evolution_proposal(proposal_id: str, req: ProposalActionReq):
    _require_enabled()
    try:
        proposal, action = evolution_service.apply_proposal(proposal_id, actor=req.actor, reason=req.reason)
        return {"proposal": proposal.model_dump(mode="json"), "action": action.model_dump(mode="json")}
    except ValueError as e:
        raise bad_request("EVOLUTION_INVALID_TRANSITION", str(e))


@router.post("/evolution/proposals/{proposal_id}/rollback")
async def rollback_evolution_proposal(proposal_id: str, req: ProposalActionReq):
    _require_enabled()
    try:
        proposal, action = evolution_service.rollback_proposal(proposal_id, actor=req.actor, reason=req.reason)
        return {"proposal": proposal.model_dump(mode="json"), "action": action.model_dump(mode="json")}
    except ValueError as e:
        raise bad_request("EVOLUTION_INVALID_TRANSITION", str(e))


@router.get("/evolution/schedule")
async def get_evolution_schedule_status():
    _require_enabled()
    return evolution_scheduler.status()


@router.post("/evolution/schedule/run")
async def run_evolution_schedule(req: EvolutionScheduleRunReq):
    _require_enabled()
    payload = evolution_scheduler.run_cycle(limit=req.limit)
    return payload
