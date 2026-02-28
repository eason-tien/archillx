from __future__ import annotations

from typing import Any, Dict, List

from ..entropy_engine import entropy_engine


class HealthProbe:
    """Probe wrapper that maps entropy outputs to health verdicts."""

    def assess(
        self,
        indicators: Dict[str, Any],
        recent_scores: List[float] | None = None,
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        entropy = entropy_engine.evaluate(indicators, recent_scores, options)
        healthy = entropy.get("stage") in ("NORMAL", "GUARDED")
        return {
            "healthy": healthy,
            "stage": entropy.get("stage"),
            "entropy": entropy,
            "reason": "stable" if healthy else "instability_detected",
        }


health_probe = HealthProbe()
