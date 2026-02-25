"""
ArcHillx — Tier Classifier
=========================
Classifies a RemediationPlan into an autonomy execution tier:
  TIER_1_AUTO   — LOW risk  → auto-execute
  TIER_2_SHADOW — MEDIUM risk → shadow run, verify, then auto
  TIER_3_MANUAL — HIGH risk  → require manual confirmation

No external dependencies.
"""
from __future__ import annotations

from typing import Any, Dict, List


class AutonomyTier:
    TIER_1 = "TIER_1_AUTO"
    TIER_2 = "TIER_2_SHADOW"
    TIER_3 = "TIER_3_MANUAL"


class TierClassifier:
    """
    Classify a RemediationPlan dict (or object with .steps / .risk_level)
    into an autonomy tier.
    """

    def classify_plan(self, plan: Any) -> Dict[str, Any]:
        """
        Returns:
          {
            "tier": str,
            "risk_level": "LOW" | "MEDIUM" | "HIGH",
            "reasons": List[str],
            "confidence": float,
          }
        """
        reasons: List[str] = []
        max_step_risk = "LOW"

        steps = getattr(plan, "steps", None) or []
        plan_risk_level = getattr(plan, "risk_level", "LOW") or "LOW"

        for step in steps:
            action = step.get("action", {})
            atype = action.get("type")
            params = action.get("params", {})

            if atype in ("delete", "drop", "terminate"):
                max_step_risk = "HIGH"
                reasons.append(f"Destructive action: {atype}")

            elif atype == "fallback":
                if max_step_risk != "HIGH":
                    max_step_risk = "MEDIUM"
                reasons.append("Model fallback switch")

            elif atype == "config":
                if params.get("timeout", 0) > 120:
                    if max_step_risk != "HIGH":
                        max_step_risk = "MEDIUM"
                    reasons.append("Large timeout increase")
                elif params.get("workers", 10) < 2:
                    if max_step_risk != "HIGH":
                        max_step_risk = "MEDIUM"
                    reasons.append("Severe concurrency reduction")

            elif atype in ("retry", "retry_with_backoff"):
                pass  # LOW risk — no change

            elif atype is not None:
                max_step_risk = "HIGH"
                reasons.append(f"Unknown action type: {atype}")

        # Determine tier from step risk
        if max_step_risk == "LOW":
            tier = AutonomyTier.TIER_1
        elif max_step_risk == "MEDIUM":
            tier = AutonomyTier.TIER_2
        else:
            tier = AutonomyTier.TIER_3

        # Override with plan-level risk
        if plan_risk_level == "HIGH":
            tier = AutonomyTier.TIER_3
            reasons.append("Plan explicitly marked HIGH risk")
        elif plan_risk_level == "MEDIUM" and tier == AutonomyTier.TIER_1:
            tier = AutonomyTier.TIER_2
            reasons.append("Plan explicitly marked MEDIUM risk")

        return {
            "tier": tier,
            "risk_level": max_step_risk,
            "reasons": reasons,
            "confidence": 1.0,
        }
