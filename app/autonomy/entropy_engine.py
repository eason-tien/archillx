"""
ArcHillx — Advanced Entropy Engine
===================================
Computes a normalized system entropy score from runtime instability indicators
and derives stability-oriented control signals.

Purpose:
- Quantify system disorder / instability using multi-signal input.
- Provide stable control outputs (anti-jitter) for autonomy/self-healing.
- Surface trend/volatility/confidence for operational decisions.
"""
from __future__ import annotations

import math
from statistics import pstdev
from typing import Any, Dict, List


class EntropyEngine:
    """Stateless entropy scorer with stability reinforcement signals."""

    _DEFAULT_WEIGHTS: Dict[str, float] = {
        "agent_disconnect_rate": 1.0,
        "task_failure_rate": 1.0,
        "latency_p95": 0.8,
        "queue_backlog": 0.7,
        "memory_pressure": 0.7,
        "provider_error_rate": 0.8,
        "governor_block_rate": 0.5,
    }

    _DEFAULT_OPTIONS: Dict[str, float] = {
        "smoothing_alpha": 0.35,
        "high_threshold": 65.0,
        "critical_threshold": 85.0,
        "hysteresis": 5.0,
    }

    def evaluate(
        self,
        indicators: Dict[str, Any],
        recent_scores: List[float] | None = None,
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        opts = self._normalize_options(options or {})
        cleaned = self._normalize_indicators(indicators)
        history = self._sanitize_history(recent_scores or [])

        if not cleaned:
            return {
                "entropy_score": 0.0,
                "smoothed_entropy": round(self._ewma(history, opts["smoothing_alpha"]), 2),
                "instability_score": 0.0,
                "shannon_entropy": 0.0,
                "volatility": round(self._volatility(history), 2),
                "stability_index": round(max(0.0, 100.0 - self._volatility(history)), 2),
                "level": "LOW",
                "stage": "NORMAL",
                "trend": self._trend(history),
                "takeover_recommended": False,
                "confidence": self._confidence(0, len(history)),
                "top_indicators": [],
                "recommendations": ["No indicators provided"],
            }

        weighted = []
        total_w = 0.0
        for name, value in cleaned.items():
            w = self._DEFAULT_WEIGHTS.get(name, 0.6)
            weighted.append((name, value, w))
            total_w += w

        instability = sum(v * w for _, v, w in weighted) / max(total_w, 1e-9)

        mass = sum(v for _, v, _ in weighted)
        if mass <= 1e-9:
            shannon = 0.0
        else:
            probs = [v / mass for _, v, _ in weighted if v > 0]
            shannon_raw = -sum(p * math.log(p, 2) for p in probs)
            shannon_max = math.log(max(len(probs), 1), 2) if probs else 1.0
            shannon = 0.0 if shannon_max == 0 else shannon_raw / shannon_max

        entropy = (0.4 * instability + 0.6 * shannon) * 100.0
        entropy = round(max(0.0, min(100.0, entropy)), 2)

        merged_series = history + [entropy]
        smoothed = self._ewma(merged_series, opts["smoothing_alpha"])
        volatility = self._volatility(merged_series)

        level = self._level(entropy)
        stage = self._stage(smoothed, opts)
        top = sorted(weighted, key=lambda x: x[1] * x[2], reverse=True)[:3]
        top_indicators = [{"name": n, "value": round(v, 4), "weight": w} for n, v, w in top]

        trend = self._trend(merged_series)
        takeover = self._takeover_recommended(smoothed, trend, opts)
        recommendations = self._recommend(level, stage, top, takeover)

        stability_index = max(0.0, min(100.0, 100.0 - (0.7 * smoothed + 0.3 * volatility)))

        return {
            "entropy_score": entropy,
            "smoothed_entropy": round(smoothed, 2),
            "instability_score": round(instability * 100.0, 2),
            "shannon_entropy": round(shannon * 100.0, 2),
            "volatility": round(volatility, 2),
            "stability_index": round(stability_index, 2),
            "level": level,
            "stage": stage,
            "trend": trend,
            "takeover_recommended": takeover,
            "confidence": self._confidence(len(cleaned), len(history)),
            "top_indicators": top_indicators,
            "recommendations": recommendations,
        }

    def _normalize_indicators(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        normalized: Dict[str, float] = {}
        for key, raw in (indicators or {}).items():
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            normalized[key] = max(0.0, min(1.0, value))
        return normalized

    def _normalize_options(self, options: Dict[str, Any]) -> Dict[str, float]:
        out = dict(self._DEFAULT_OPTIONS)
        for k in out:
            if k in options:
                try:
                    out[k] = float(options[k])
                except (TypeError, ValueError):
                    continue
        out["smoothing_alpha"] = max(0.05, min(0.95, out["smoothing_alpha"]))
        out["high_threshold"] = max(40.0, min(90.0, out["high_threshold"]))
        out["critical_threshold"] = max(out["high_threshold"] + 5.0, min(99.0, out["critical_threshold"]))
        out["hysteresis"] = max(1.0, min(20.0, out["hysteresis"]))
        return out

    def _sanitize_history(self, history: List[Any]) -> List[float]:
        cleaned = []
        for raw in history:
            try:
                v = float(raw)
            except (TypeError, ValueError):
                continue
            cleaned.append(max(0.0, min(100.0, v)))
        return cleaned[-20:]

    def _level(self, entropy_score: float) -> str:
        if entropy_score < 35:
            return "LOW"
        if entropy_score < 65:
            return "MEDIUM"
        if entropy_score < 85:
            return "HIGH"
        return "CRITICAL"

    def _stage(self, smoothed_entropy: float, opts: Dict[str, float]) -> str:
        if smoothed_entropy >= opts["critical_threshold"]:
            return "EMERGENCY"
        if smoothed_entropy >= opts["high_threshold"]:
            return "UNSTABLE"
        if smoothed_entropy >= (opts["high_threshold"] - opts["hysteresis"]):
            return "DEGRADED"
        if smoothed_entropy >= 35:
            return "GUARDED"
        return "NORMAL"

    def _trend(self, recent: List[float]) -> str:
        if len(recent) < 2:
            return "STABLE"
        first, last = float(recent[0]), float(recent[-1])
        delta = last - first
        if delta >= 12:
            return "RISING_FAST"
        if delta >= 4:
            return "RISING"
        if delta <= -12:
            return "FALLING_FAST"
        if delta <= -4:
            return "FALLING"
        return "STABLE"

    def _ewma(self, series: List[float], alpha: float) -> float:
        if not series:
            return 0.0
        val = float(series[0])
        for p in series[1:]:
            val = alpha * float(p) + (1 - alpha) * val
        return max(0.0, min(100.0, val))

    def _volatility(self, series: List[float]) -> float:
        if len(series) < 2:
            return 0.0
        return max(0.0, min(100.0, pstdev(series)))

    def _takeover_recommended(self, smoothed: float, trend: str, opts: Dict[str, float]) -> bool:
        if smoothed >= opts["critical_threshold"]:
            return True
        if smoothed >= opts["high_threshold"] and trend in ("RISING", "RISING_FAST"):
            return True
        return False

    def _confidence(self, indicator_count: int, history_count: int) -> float:
        raw = min(1.0, (indicator_count / 7.0) * 0.7 + min(history_count, 10) / 10.0 * 0.3)
        return round(raw, 3)

    def _recommend(self, level: str, stage: str, top: List[tuple], takeover: bool) -> List[str]:
        hints = []
        for name, _, _ in top:
            if name == "agent_disconnect_rate":
                hints.append("Validate agent connectivity and restart unhealthy workers")
            elif name == "task_failure_rate":
                hints.append("Pause risky automations and inspect recent failed tasks")
            elif name == "latency_p95":
                hints.append("Enable degraded mode and reduce concurrent workload")
            elif name == "provider_error_rate":
                hints.append("Switch model provider fallback chain and retry budget")
            elif name == "memory_pressure":
                hints.append("Trigger cache cleanup and increase memory headroom")
            elif name == "queue_backlog":
                hints.append("Throttle incoming jobs and scale workers")

        if stage in ("DEGRADED", "UNSTABLE", "EMERGENCY"):
            hints.append("Enable self-healing probe escalation")
        if takeover:
            hints.append("Enter self-healing takeover and controlled handoff workflow")
        if level in ("HIGH", "CRITICAL"):
            hints.append("Increase observability sampling and alert sensitivity")
        if not hints:
            hints.append("Keep monitoring indicators")
        return hints[:6]


entropy_engine = EntropyEngine()
