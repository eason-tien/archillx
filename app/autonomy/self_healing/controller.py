from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

from ...config import settings
from .health_probe import health_probe
from .models import SelfHealingEvent, SelfHealingState


class SelfHealingController:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state = SelfHealingState.IDLE
        self._fail_streak = 0
        self._recover_streak = 0
        self._cooldown_until = 0.0
        self._events: List[SelfHealingEvent] = []
        self._last_entropy_scores: List[float] = []

    def _emit(self, phase: str, action: str, result: str, detail: Dict[str, Any] | None = None) -> None:
        self._events.append(SelfHealingEvent(phase=phase, action=action, result=result, detail=detail or {}))
        self._events = self._events[-500:]

    def status(self) -> dict:
        with self._lock:
            return {
                "enabled": settings.enable_self_healing,
                "state": self._state.value,
                "fail_streak": self._fail_streak,
                "recover_streak": self._recover_streak,
                "cooldown_until": self._cooldown_until,
                "last_entropy_scores": self._last_entropy_scores[-10:],
            }

    def list_events(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return [e.to_dict() for e in self._events[-max(1, min(limit, 200)):]]

    def start(self, reason: str = "manual", force: bool = False) -> dict:
        with self._lock:
            if self._state not in (SelfHealingState.IDLE, SelfHealingState.DEGRADED) and not force:
                return {"started": False, "state": self._state.value, "reason": "already_active"}
            self._state = SelfHealingState.TAKEOVER
            self._fail_streak = 0
            self._recover_streak = 0
            self._emit("TAKEOVER", "start", "ok", {"reason": reason, "force": force})
            self._state = SelfHealingState.REPAIRING
            self._emit("REPAIRING", "bootstrap_repair", "ok")
            self._state = SelfHealingState.VERIFYING
            return {"started": True, "state": self._state.value}

    def stop(self, reason: str = "manual") -> dict:
        with self._lock:
            prev = self._state
            self._state = SelfHealingState.IDLE
            self._fail_streak = 0
            self._recover_streak = 0
            self._cooldown_until = 0.0
            self._emit("IDLE", "stop", "ok", {"reason": reason, "prev_state": prev.value})
            return {"stopped": True, "state": self._state.value}

    def handoff(self, reason: str = "manual") -> dict:
        with self._lock:
            self._state = SelfHealingState.HANDOFF
            self._emit("HANDOFF", "handoff", "ok", {"reason": reason})
            self._state = SelfHealingState.COOLDOWN
            self._cooldown_until = time.monotonic() + settings.self_heal_cooldown_s
            return {"handoff": True, "state": self._state.value}

    def tick(
        self,
        indicators: Dict[str, Any],
        options: Dict[str, Any] | None = None,
        recent_scores: List[float] | None = None,
    ) -> dict:
        with self._lock:
            if not settings.enable_self_healing:
                return {"ok": False, "error": "self-healing disabled"}

            external_history = recent_scores if recent_scores is not None else self._last_entropy_scores
            probe = health_probe.assess(indicators, external_history, options)
            entropy_score = float(probe["entropy"]["entropy_score"])
            self._last_entropy_scores = (self._last_entropy_scores + [entropy_score])[-20:]

            if self._state == SelfHealingState.COOLDOWN and time.monotonic() >= self._cooldown_until:
                self._state = SelfHealingState.IDLE
                self._emit("IDLE", "cooldown_finished", "ok")

            if probe["healthy"]:
                self._recover_streak += 1
                self._fail_streak = 0
            else:
                self._fail_streak += 1
                self._recover_streak = 0

            if self._state == SelfHealingState.IDLE and not probe["healthy"]:
                self._state = SelfHealingState.DEGRADED
                self._emit("DEGRADED", "degrade_detected", "warn", {"stage": probe["stage"]})

            if self._state in (SelfHealingState.IDLE, SelfHealingState.DEGRADED):
                if self._fail_streak >= settings.self_heal_fail_threshold or probe["entropy"].get("takeover_recommended"):
                    self.start(reason="auto_takeover", force=True)

            if self._state == SelfHealingState.VERIFYING:
                if self._recover_streak >= settings.self_heal_recover_threshold:
                    self._state = SelfHealingState.HANDOFF_READY
                    self._emit("HANDOFF_READY", "recovery_verified", "ok")
                    self.handoff(reason="auto_handoff")
                elif self._fail_streak >= settings.self_heal_fail_threshold:
                    self._state = SelfHealingState.REPAIRING
                    self._emit("REPAIRING", "retry_repair", "warn")
                    self._state = SelfHealingState.VERIFYING

            return {
                "ok": True,
                "state": self._state.value,
                "probe": probe,
                "fail_streak": self._fail_streak,
                "recover_streak": self._recover_streak,
            }


self_healing_controller = SelfHealingController()
