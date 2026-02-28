from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .proposal_store import latest_json, write_json
from .risk_scoring import score_plan_item
from .patch_artifacts import render_patch_artifacts
from .schemas import EvolutionPlan, EvolutionPlanItem, EvolutionProposal, EvolutionProposalChange


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_tests(item: EvolutionPlanItem) -> list[str]:
    return [scope for scope in item.suggested_scope if scope.startswith("tests/") or "/tests/" in scope]


def _rollout_notes(item: EvolutionPlanItem, risk_level: str) -> list[str]:
    notes = [
        "Run compileall and targeted pytest before merge.",
        "Attach proposal evidence to release/rollback gate review.",
    ]
    if risk_level in ("medium", "high"):
        notes.append("Require human approval before patch application.")
    if item.priority == "P0":
        notes.append("Validate rollback path and restore drill confidence before rollout.")
    return notes


def _summary_for(item: EvolutionPlanItem) -> str:
    return f"Candidate patch proposal for {item.subject}: {item.title}. Expected benefit: {item.expected_benefit}."


class PatchProposer:
    def generate(self, plan: EvolutionPlan | None = None, item_index: int = 0) -> EvolutionProposal:
        if plan is None:
            latest = latest_json("plans")
            if latest is None:
                from .evolution_planner import EvolutionPlanner
                plan = EvolutionPlanner().build()
            else:
                plan = EvolutionPlan.model_validate(latest)
        if not plan.items:
            raise ValueError("No evolution plan items available for proposal generation.")
        if item_index < 0 or item_index >= len(plan.items):
            raise IndexError("Proposal item index out of range.")
        item = plan.items[item_index]
        risk = score_plan_item(item)
        changes = [
            EvolutionProposalChange(file=scope, action=("modify" if not scope.startswith("tests/") else "add"), rationale=f"Suggested by evolution planner for subject {item.subject}.")
            for scope in item.suggested_scope
        ] or [EvolutionProposalChange(file="docs/EVOLUTION_DESIGN.md", action="review", rationale="No code scope identified; document investigation first.")]
        proposal = EvolutionProposal(
            proposal_id=f"prop_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}",
            created_at=_now_iso(),
            plan_id=plan.plan_id,
            inspection_id=plan.inspection_id,
            source_subject=item.subject,
            title=f"Patch proposal: {item.title}",
            summary=_summary_for(item),
            suggested_changes=changes,
            tests_to_add=_default_tests(item),
            rollout_notes=_rollout_notes(item, risk.risk_level),
            requires_human_review=item.requires_human_review or risk.risk_level != "low",
            risk=risk,
        )
        path = write_json("proposals", proposal.proposal_id, proposal.model_dump(mode="json"))
        proposal.evidence_path = path
        proposal.artifact_paths = render_patch_artifacts(proposal)
        path = write_json("proposals", proposal.proposal_id, proposal.model_dump(mode="json"))
        proposal.evidence_path = path
        return proposal
