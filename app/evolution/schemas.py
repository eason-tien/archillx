from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EvolutionSignalSnapshot(BaseModel):
    created_at: str
    readiness: dict[str, Any]
    migration: dict[str, Any]
    telemetry: dict[str, Any]
    audit_summary: dict[str, Any]
    gate_summary: dict[str, Any]


class EvolutionFinding(BaseModel):
    category: Literal[
        "security",
        "stability",
        "reliability",
        "performance",
        "operability",
        "deployment_gap",
        "migration_gap",
        "test_gap",
        "docs_gap",
    ]
    severity: Literal["critical", "high", "medium", "low"]
    subject: str
    signal: str
    summary: str
    value: Any = None
    confidence: float = 0.5
    evidence: list[str] = Field(default_factory=list)
    requires_human_review: bool = True


class EvolutionInspectionReport(BaseModel):
    inspection_id: str
    created_at: str
    status: Literal["ok", "attention", "critical"]
    findings: list[EvolutionFinding] = Field(default_factory=list)
    signal_snapshot: EvolutionSignalSnapshot
    evidence_path: str | None = None


class EvolutionPlanItem(BaseModel):
    priority: Literal["P0", "P1", "P2"]
    category: str
    title: str
    subject: str
    expected_benefit: str
    suggested_scope: list[str] = Field(default_factory=list)
    requires_human_review: bool = True
    source_inspection_id: str | None = None


class EvolutionPlan(BaseModel):
    plan_id: str
    created_at: str
    inspection_id: str | None = None
    items: list[EvolutionPlanItem] = Field(default_factory=list)
    evidence_path: str | None = None


class EvolutionRiskAssessment(BaseModel):
    risk_score: int = 0
    risk_level: Literal["low", "medium", "high"] = "low"
    factors: list[str] = Field(default_factory=list)
    auto_apply_allowed: bool = False


class EvolutionProposalChange(BaseModel):
    file: str
    action: Literal["add", "modify", "review"] = "review"
    rationale: str | None = None


class EvolutionProposal(BaseModel):
    proposal_id: str
    created_at: str
    plan_id: str | None = None
    inspection_id: str | None = None
    source_subject: str
    title: str
    summary: str
    suggested_changes: list[EvolutionProposalChange] = Field(default_factory=list)
    tests_to_add: list[str] = Field(default_factory=list)
    rollout_notes: list[str] = Field(default_factory=list)
    requires_human_review: bool = True
    risk: EvolutionRiskAssessment
    status: Literal["generated", "guard_passed", "guard_failed", "approved", "rejected", "applied", "rolled_back"] = "generated"
    approval_required: bool = True
    approved_by: str | None = None
    rejected_by: str | None = None
    applied_by: str | None = None
    rolled_back_by: str | None = None
    approved_at: str | None = None
    rejected_at: str | None = None
    applied_at: str | None = None
    rolled_back_at: str | None = None
    last_guard_id: str | None = None
    last_baseline_id: str | None = None
    evidence_path: str | None = None
    artifact_paths: dict[str, str] = Field(default_factory=dict)




class EvolutionBaselinePoint(BaseModel):
    readiness_status: str = "unknown"
    migration_status: str = "unknown"
    http_5xx_total: int = 0
    skill_failure_total: int = 0
    sandbox_blocked_total: int = 0
    governor_blocked_total: int = 0
    release_failed_total: int = 0
    rollback_failed_total: int = 0


class EvolutionBaselineCompare(BaseModel):
    baseline_id: str
    created_at: str
    proposal_id: str | None = None
    inspection_id: str | None = None
    before: EvolutionBaselinePoint
    after: EvolutionBaselinePoint
    diff: dict[str, int | str] = Field(default_factory=dict)
    regression_detected: bool = False
    summary: list[str] = Field(default_factory=list)
    evidence_path: str | None = None

class EvolutionGuardCheck(BaseModel):
    name: str
    status: Literal["passed", "failed", "skipped"]
    detail: str = ""
    command: str | None = None


class EvolutionGuardRun(BaseModel):
    guard_id: str
    created_at: str
    proposal_id: str | None = None
    mode: Literal["quick", "full"] = "quick"
    status: Literal["passed", "failed"]
    checks: list[EvolutionGuardCheck] = Field(default_factory=list)
    evidence_path: str | None = None


class EvolutionApprovalAction(BaseModel):
    action_id: str
    created_at: str
    proposal_id: str
    action: Literal["approve", "reject", "apply", "rollback"]
    actor: str = "operator"
    reason: str | None = None
    from_status: str
    to_status: str
    evidence_path: str | None = None
