"""
ArcHillx — Multi-Agent Circuit Breaker
=======================================
Rules:
  per-task : >= 3 REJECTs on a single task → auto VETO + 10-minute freeze
  global   : >= 5 consecutive VETOs         → global LIMITED mode

Standalone — no MGIS imports.
"""
from __future__ import annotations

import time
from typing import Dict, List

from .types import SystemMode


class CircuitBreaker:
    """
    Pure in-memory circuit breaker.

    Note: In a multi-worker deployment each process has its own instance.
    For production multi-worker deployments, persist state to a shared DB table.
    """

    _REJECT_THRESHOLD  = 3      # per-task cumulative REJECT limit
    _FREEZE_SECONDS    = 600    # freeze duration: 10 minutes
    _GLOBAL_VETO_LIMIT = 5      # global consecutive VETO limit

    def __init__(self) -> None:
        self._reject_counts:     Dict[str, int]   = {}
        self._frozen_until:      Dict[str, float] = {}
        self._consecutive_vetos: int              = 0
        self._global_mode:       SystemMode       = SystemMode.NORMAL

    # ── Per-task API ──────────────────────────────────────────────────────────

    def record_reject(self, task_id: str) -> bool:
        """
        Record one REJECT for task_id.
        Returns True when the threshold is exceeded — caller should issue VETO and freeze.
        """
        self._reject_counts[task_id] = self._reject_counts.get(task_id, 0) + 1
        if self._reject_counts[task_id] >= self._REJECT_THRESHOLD:
            self._frozen_until[task_id] = time.monotonic() + self._FREEZE_SECONDS
            return True
        return False

    def is_frozen(self, task_id: str) -> bool:
        """Check whether a task is within its freeze window. Auto-thaws when expired."""
        deadline = self._frozen_until.get(task_id, 0.0)
        if deadline and time.monotonic() < deadline:
            return True
        # Thaw: clear records so the task can be resubmitted
        if task_id in self._frozen_until:
            del self._frozen_until[task_id]
            self._reject_counts.pop(task_id, None)
        return False

    def reject_count(self, task_id: str) -> int:
        return self._reject_counts.get(task_id, 0)

    # ── Global API ────────────────────────────────────────────────────────────

    def record_veto(self) -> None:
        """Record a global VETO; enter LIMITED mode when consecutive limit is reached."""
        self._consecutive_vetos += 1
        if self._consecutive_vetos >= self._GLOBAL_VETO_LIMIT:
            self._global_mode = SystemMode.LIMITED

    def reset_veto_streak(self) -> None:
        """An APPROVE event resets the consecutive VETO counter and returns to NORMAL."""
        self._consecutive_vetos = 0
        self._global_mode       = SystemMode.NORMAL

    @property
    def mode(self) -> SystemMode:
        return self._global_mode

    @property
    def consecutive_vetos(self) -> int:
        return self._consecutive_vetos

    def frozen_tasks(self) -> List[str]:
        """Return task IDs currently within their freeze window."""
        now = time.monotonic()
        return [t for t, deadline in self._frozen_until.items() if deadline > now]
