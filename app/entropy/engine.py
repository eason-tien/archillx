from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import pstdev
from typing import Any

from ..config import settings

try:
    import fcntl  # type: ignore
except Exception:  # pragma: no cover
    fcntl = None

try:
    import msvcrt  # type: ignore
except Exception:  # pragma: no cover
    msvcrt = None
from ..utils.telemetry import telemetry


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EntropySnapshot:
    timestamp: str
    entropy_score: float
    entropy_vector: dict[str, float]
    risk_level: str
    state: str
    triggered_action: list[str]
    recovery_time: float | None
    governor_override: bool
    ewma: float
    volatility: float
    forecast_window_s: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "ts": self.timestamp,
            "entropy_score": self.entropy_score,
            "score": self.entropy_score,
            "entropy_vector": self.entropy_vector,
            "vector": self.entropy_vector,
            "risk_level": self.risk_level,
            "risk": self.risk_level,
            "state": self.state,
            "triggered_action": self.triggered_action,
            "recovery_time": self.recovery_time,
            "governor_override": self.governor_override,
            "predictor": {
                "ewma": self.ewma,
                "volatility": self.volatility,
                "forecast_window_s": self.forecast_window_s,
            },
            "version": "Entropy Engine v1.0",
        }


class EntropyEngine:
    """Entropy Engine v1.0 (static weights + EWMA + rule actuator)."""

    def __init__(self) -> None:
        self.weights = self._load_weights()
        self._current_state = "NORMAL"
        self._ewma: float | None = None
        self._score_window: deque[float] = deque(maxlen=max(10, int(settings.entropy_volatility_window)))
        self._last_recovery_start_ts: float | None = None
        self._last_snapshot: dict[str, Any] | None = None
        self._last_tick_ts: float = 0.0
        self._io_lock = threading.Lock()

    def _load_weights(self) -> dict[str, float]:
        defaults = {"memory": 0.2, "task": 0.2, "model": 0.2, "resource": 0.2, "decision": 0.2}
        raw = str(getattr(settings, "entropy_weights", "") or "").strip()
        if not raw:
            return defaults
        parsed = dict(defaults)
        try:
            for seg in raw.split(","):
                if "=" not in seg:
                    continue
                k, v = seg.split("=", 1)
                key = k.strip().lower()
                if key in parsed:
                    parsed[key] = max(0.0, float(v.strip()))
            total = sum(parsed.values())
            if total > 0:
                parsed = {k: round(v / total, 6) for k, v in parsed.items()}
            return parsed
        except Exception:
            return defaults

    def _evidence_path(self) -> Path:
        p = Path(settings.evidence_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p / "entropy_engine.jsonl"

    def _append_evidence(self, payload: dict[str, Any]) -> None:
        out = self._evidence_path()
        line = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        with self._io_lock:
            with out.open("ab") as f:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                elif msvcrt is not None:
                    msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    f.write(line)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    if fcntl is not None:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    elif msvcrt is not None:
                        try:
                            f.seek(max(0, f.tell() - 1))
                        except Exception:
                            pass
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

    def _collect_memory_entropy(self) -> float:
        try:
            from ..db.schema import AHMemory, SessionLocal

            db = SessionLocal()
            try:
                rows = db.query(AHMemory).order_by(AHMemory.created_at.desc()).limit(200).all()
                if not rows:
                    return 0.0
                contents = [str(r.content or "").strip().lower() for r in rows]
                non_empty = [c for c in contents if c]
                unique = len(set(non_empty)) if non_empty else 0
                duplicate_ratio = 1.0 - (unique / max(1, len(non_empty)))
                low_importance_ratio = sum(1 for r in rows if float(getattr(r, "importance", 0.5) or 0.5) < 0.2) / len(rows)
                return _clamp01(0.65 * duplicate_ratio + 0.35 * low_importance_ratio)
            finally:
                db.close()
        except Exception:
            return 0.0

    def _collect_task_entropy(self) -> float:
        try:
            from ..db.schema import AHTask, SessionLocal

            db = SessionLocal()
            try:
                rows = db.query(AHTask).order_by(AHTask.created_at.desc()).limit(300).all()
                if not rows:
                    return 0.0
                unfinished = sum(1 for r in rows if str(r.status) not in {"closed", "completed"}) / len(rows)
                failed = sum(1 for r in rows if str(r.status) in {"failed"}) / len(rows)
                now = _utcnow()
                one_hour = now - timedelta(hours=1)
                created_1h = sum(1 for r in rows if getattr(r, "created_at", now) and r.created_at.replace(tzinfo=timezone.utc) >= one_hour)
                closed_1h = sum(1 for r in rows if getattr(r, "closed_at", None) and r.closed_at.replace(tzinfo=timezone.utc) >= one_hour)
                backlog_slope = _clamp01((created_1h - closed_1h) / max(1, created_1h + closed_1h + 1))
                return _clamp01(0.50 * unfinished + 0.30 * failed + 0.20 * backlog_slope)
            finally:
                db.close()
        except Exception:
            return 0.0

    def _collect_model_entropy(self) -> float:
        try:
            agg = telemetry.aggregated_snapshot() or {}
            gov = agg.get("governor", {}).get("decisions", {})
            blocked = float(gov.get("blocked", 0))
            warned = float(gov.get("warned", 0))
            approved = float(gov.get("approved", 0))
            total = blocked + warned + approved
            fallback_ratio = (blocked + warned) / total if total > 0 else 0.0

            from ..db.schema import AHTask, SessionLocal

            db = SessionLocal()
            try:
                rows = db.query(AHTask).order_by(AHTask.created_at.desc()).limit(150).all()
                models = [str(r.model_used or "") for r in rows if str(r.model_used or "").strip()]
                diversity = (len(set(models)) / max(1, len(models))) if models else 0.0
            finally:
                db.close()
            divergence = _clamp01(diversity)
            return _clamp01(0.55 * fallback_ratio + 0.45 * divergence)
        except Exception:
            return 0.0

    def _collect_resource_entropy(self) -> float:
        try:
            hist = telemetry.history_snapshot() or {}
            w = hist.get("windows", {}).get("last_60s", {})
            http = w.get("http", {})
            lat = http.get("latency", {})
            avg_s = float(lat.get("avg_s", 0.0))
            c5 = float(http.get("status", {}).get("5xx", 0))
            req = float(http.get("requests_total", 0))
            err_ratio = (c5 / req) if req > 0 else 0.0
            rate_limited = float(http.get("rate_limited_total", 0))
            latency_norm = _clamp01(avg_s / 1.5)
            rate_limited_norm = _clamp01(rate_limited / 20.0)
            return _clamp01(0.45 * latency_norm + 0.40 * err_ratio + 0.15 * rate_limited_norm)
        except Exception:
            return 0.0

    def _collect_decision_entropy(self) -> float:
        try:
            from ..db.schema import AHAuditLog, SessionLocal

            db = SessionLocal()
            try:
                rows = db.query(AHAuditLog).order_by(AHAuditLog.created_at.desc()).limit(200).all()
                if not rows:
                    return 0.0
                decisions = [str(r.decision or "") for r in rows]
                warned_blocked = sum(1 for d in decisions if d in {"WARNED", "BLOCKED"}) / len(decisions)
                risks = [float(getattr(r, "risk_score", 0) or 0) for r in rows]
                drift = _clamp01(pstdev(risks) / 40.0) if len(risks) > 1 else 0.0
                return _clamp01(0.60 * warned_blocked + 0.40 * drift)
            finally:
                db.close()
        except Exception:
            return 0.0

    def collect_vector(self) -> dict[str, float]:
        return {
            "memory": round(self._collect_memory_entropy(), 4),
            "task": round(self._collect_task_entropy(), 4),
            "model": round(self._collect_model_entropy(), 4),
            "resource": round(self._collect_resource_entropy(), 4),
            "decision": round(self._collect_decision_entropy(), 4),
        }

    def calculate_score(self, vector: dict[str, float]) -> float:
        score = sum(float(vector.get(k, 0.0)) * float(w) for k, w in self.weights.items())
        return round(_clamp01(score), 4)

    def _predict(self, score: float) -> tuple[float, float, int]:
        alpha = _clamp01(float(getattr(settings, "entropy_ewma_alpha", 0.35))) or 0.35
        self._ewma = score if self._ewma is None else (alpha * score + (1.0 - alpha) * self._ewma)
        self._score_window.append(score)
        vol = pstdev(self._score_window) if len(self._score_window) > 1 else 0.0
        if self._ewma >= float(settings.entropy_threshold_degraded):
            window = 300
        elif self._ewma >= float(settings.entropy_threshold_warn):
            window = 600
        elif self._ewma >= float(settings.entropy_threshold_normal):
            window = 1200
        else:
            window = 1800
        return round(float(self._ewma), 4), round(float(vol), 4), int(window)

    def _risk_level(self, score: float) -> str:
        if score < float(settings.entropy_threshold_normal):
            return "NORMAL"
        if score < float(settings.entropy_threshold_warn):
            return "WARN"
        if score < float(settings.entropy_threshold_degraded):
            return "DEGRADED"
        return "CRITICAL"

    def _transition_state(self, base: str) -> tuple[str, float | None, str]:
        now = time.time()
        recovery_time = None
        prev = self._current_state

        if prev in {"DEGRADED", "CRITICAL"} and base in {"NORMAL", "WARN"}:
            self._current_state = "RECOVERY"
            self._last_recovery_start_ts = now
        elif prev == "RECOVERY":
            self._current_state = base
            if self._last_recovery_start_ts is not None:
                recovery_time = round(max(0.0, now - self._last_recovery_start_ts), 3)
                self._last_recovery_start_ts = None
        else:
            self._current_state = base

        return self._current_state, recovery_time, prev

    def _actuator(self, vector: dict[str, float], state: str) -> list[str]:
        if state == "NORMAL":
            return []
        actions: list[str] = []
        if vector.get("memory", 0) >= 0.6:
            actions.append("Memory Compaction")
        if vector.get("task", 0) >= 0.6:
            actions.append("Task Rebalancing")
        if vector.get("model", 0) >= 0.6:
            actions.append("Router Reset / Fallback Tighten")
        if vector.get("resource", 0) >= 0.6:
            actions.append("Circuit Mode Shift")
        if vector.get("decision", 0) >= 0.6:
            actions.append("Goal Re-alignment")
        if not actions and state in {"DEGRADED", "CRITICAL"}:
            actions = ["Stability Review"]
        return actions

    def _evaluate_with_vector(self, vector: dict[str, float], persist: bool, governor_override: bool = False) -> dict[str, Any]:
        score = self.calculate_score(vector)
        ewma, vol, forecast_window = self._predict(score)
        base_risk = self._risk_level(score)
        state, recovery_time, prev = self._transition_state(base_risk)
        actions = self._actuator(vector, state)

        snap = EntropySnapshot(
            timestamp=_utcnow().isoformat(),
            entropy_score=score,
            entropy_vector=vector,
            risk_level=base_risk,
            state=state,
            triggered_action=actions,
            recovery_time=recovery_time,
            governor_override=governor_override,
            ewma=ewma,
            volatility=vol,
            forecast_window_s=forecast_window,
        ).to_dict()

        telemetry.gauge("entropy_score", score)
        telemetry.gauge("entropy_ewma", ewma)
        telemetry.gauge("entropy_volatility", vol)

        if persist:
            if prev != state:
                self._append_evidence({
                    "event": "state_transition",
                    "timestamp": snap["timestamp"],
                    "from": prev,
                    "to": state,
                    "score": score,
                    "risk": base_risk,
                })
            self._append_evidence(snap)
        self._last_snapshot = snap
        return snap

    def evaluate(self, persist: bool = False) -> dict[str, Any]:
        min_interval = max(0, int(getattr(settings, "entropy_tick_min_interval_s", 5)))
        now = time.time()
        if persist and min_interval > 0 and (now - self._last_tick_ts) < min_interval:
            next_allowed = self._last_tick_ts + min_interval
            base = dict(self._last_snapshot or self.evaluate(persist=False))
            base.update({
                "skipped": True,
                "reason": "tick_min_interval_not_reached",
                "next_allowed_ts": datetime.fromtimestamp(next_allowed, tz=timezone.utc).isoformat(),
            })
            return base
        vector = self.collect_vector()
        out = self._evaluate_with_vector(vector, persist=persist, governor_override=bool(settings.governor_mode == "hard_block" and self._current_state == "CRITICAL"))
        if persist:
            self._last_tick_ts = now
            out["skipped"] = False
        return out

    def evaluate_from_vector_for_test(self, vector: dict[str, float], persist: bool = True) -> dict[str, Any]:
        norm = {k: _clamp01(float(vector.get(k, 0.0))) for k in ["memory", "task", "model", "resource", "decision"]}
        return self._evaluate_with_vector(norm, persist=persist)

    def status(self) -> dict[str, Any]:
        if self._last_snapshot is None:
            return self.evaluate(persist=False)
        return self._last_snapshot

    def evidence_sha256(self) -> str | None:
        p = self._evidence_path()
        if not p.exists():
            return None
        return hashlib.sha256(p.read_bytes()).hexdigest()


entropy_engine = EntropyEngine()
