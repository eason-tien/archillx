from __future__ import annotations

from .schemas import EvolutionPlanItem, EvolutionRiskAssessment

_HIGH_RISK_HINTS = {"sandbox", "migration", "auth", "acl", "code_exec", "file_ops", "release_gate"}


def score_plan_item(item: EvolutionPlanItem) -> EvolutionRiskAssessment:
    score = 20
    factors: list[str] = []
    text = " ".join([item.subject, item.title, item.category, *item.suggested_scope]).lower()

    if item.priority == "P0":
        score += 35
        factors.append("priority_p0")
    elif item.priority == "P1":
        score += 20
        factors.append("priority_p1")
    else:
        score += 8

    if item.requires_human_review:
        score += 15
        factors.append("requires_human_review")

    for hint in _HIGH_RISK_HINTS:
        if hint in text:
            score += 18
            factors.append(f"touches_{hint}")

    if any(scope.startswith("tests/") for scope in item.suggested_scope):
        score -= 5
        factors.append("has_test_scope")

    score = max(0, min(100, score))
    if score >= 70:
        level = "high"
    elif score >= 40:
        level = "medium"
    else:
        level = "low"
    auto_apply_allowed = level == "low" and not item.requires_human_review
    return EvolutionRiskAssessment(risk_score=score, risk_level=level, factors=factors, auto_apply_allowed=auto_apply_allowed)
