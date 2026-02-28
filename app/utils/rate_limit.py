from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Tuple


@dataclass
class LimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_after_s: int


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: Dict[Tuple[str, str], Deque[float]] = {}

    def check(self, key: str, bucket: str, limit: int, window_s: int = 60) -> LimitResult:
        now = time.time()
        k = (bucket, key)
        with self._lock:
            q = self._events.setdefault(k, deque())
            cutoff = now - window_s
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= limit:
                reset_after = max(1, int(window_s - (now - q[0]))) if q else window_s
                return LimitResult(False, limit, 0, reset_after)
            q.append(now)
            remaining = max(0, limit - len(q))
            return LimitResult(True, limit, remaining, window_s)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


rate_limiter = SlidingWindowRateLimiter()
