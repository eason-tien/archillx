from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Dict, Any


class Telemetry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._timers_sum: Dict[str, float] = defaultdict(float)
        self._timers_count: Dict[str, int] = defaultdict(int)
        self._started_at = time.time()
        self._history_windows = (60, 300, 3600)
        self._event_history = deque(maxlen=20000)
        self._timer_history = deque(maxlen=20000)

    def incr(self, name: str, value: float = 1.0) -> None:
        now = time.time()
        with self._lock:
            self._counters[name] += value
            self._event_history.append((now, name, float(value)))

    def gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def timing(self, name: str, seconds: float) -> None:
        now = time.time()
        value = max(0.0, float(seconds))
        with self._lock:
            self._timers_sum[name] += value
            self._timers_count[name] += 1
            self._timer_history.append((now, name, value))

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._timers_sum.clear()
            self._timers_count.clear()
            self._event_history.clear()
            self._timer_history.clear()
            self._started_at = time.time()
        self._history_windows = (60, 300, 3600)
        self._event_history = deque(maxlen=20000)
        self._timer_history = deque(maxlen=20000)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "uptime_s": max(0, int(time.time() - self._started_at)),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timers": {
                    name: {
                        "count": self._timers_count.get(name, 0),
                        "sum_s": round(self._timers_sum.get(name, 0.0), 6),
                        "avg_s": round(
                            (self._timers_sum.get(name, 0.0) / self._timers_count[name]) if self._timers_count.get(name, 0) else 0.0,
                            6,
                        ),
                    }
                    for name in set(self._timers_sum) | set(self._timers_count)
                },
            }

    def aggregated_snapshot(self) -> dict:
        snap = self.snapshot()
        counters = snap.get("counters", {})
        timers = snap.get("timers", {})

        def _sum_prefix(prefix: str) -> float:
            return float(sum(float(v) for k, v in counters.items() if k.startswith(prefix)))

        def _skill_name_stats(suffix: str) -> dict[str, float]:
            out: dict[str, float] = {}
            needle = suffix
            for key, value in counters.items():
                if key.startswith("skill_") and key.endswith(needle) and not key.startswith("skill_invoke") and not key.startswith("skill_validation") and not key.startswith("skill_access") and not key.startswith("skill_disabled"):
                    name = key[len("skill_"):-len(needle)]
                    out[name] = float(value)
            return dict(sorted(out.items()))

        def _cron_job_stats(suffix: str) -> dict[str, float]:
            out: dict[str, float] = {}
            needle = suffix
            for key, value in counters.items():
                if key.startswith("cron_job_") and key.endswith(needle):
                    name = key[len("cron_job_"):-len(needle)]
                    out[name] = float(value)
            return dict(sorted(out.items()))

        def _sandbox_backend_stats() -> dict[str, float]:
            out: dict[str, float] = {}
            for key, value in counters.items():
                if key.startswith("sandbox_backend_") and key.endswith("_total"):
                    name = key[len("sandbox_backend_"):-len("_total")]
                    out[name] = float(value)
            return dict(sorted(out.items()))

        def _sandbox_decision_stats() -> dict[str, float]:
            out: dict[str, float] = {}
            for key, value in counters.items():
                if key.startswith("sandbox_decision_") and key.endswith("_total"):
                    name = key[len("sandbox_decision_"):-len("_total")]
                    out[name] = float(value)
            return dict(sorted(out.items()))

        http_timer = timers.get("http_request", {"count": 0, "sum_s": 0.0, "avg_s": 0.0})
        return {
            "window": {"uptime_s": snap.get("uptime_s", 0)},
            "http": {
                "requests_total": int(counters.get("http_requests_total", 0)),
                "status": {
                    "2xx": int(_sum_prefix("http_status_2")),
                    "4xx": int(_sum_prefix("http_status_4")),
                    "5xx": int(_sum_prefix("http_status_5")),
                },
                "latency": {
                    "count": int(http_timer.get("count", 0)),
                    "sum_s": float(http_timer.get("sum_s", 0.0)),
                    "avg_s": float(http_timer.get("avg_s", 0.0)),
                },
                "auth_failed_total": int(counters.get("auth_failed_total", 0)),
                "rate_limited_total": int(counters.get("rate_limited_total", 0)),
            },
            "governor": {
                "evaluations_total": int(counters.get("governor_evaluations_total", 0)),
                "decisions": {
                    "approved": int(counters.get("governor_decision_approved_total", 0)),
                    "warned": int(counters.get("governor_decision_warned_total", 0)),
                    "blocked": int(counters.get("governor_decision_blocked_total", 0)),
                },
                "last_risk_score": float(counters.get("governor_last_risk_score", 0.0)),
            },
            "skills": {
                "totals": {
                    "invoke_total": int(counters.get("skill_invoke_total", 0)),
                    "success_total": int(counters.get("skill_invoke_success_total", 0)),
                    "failure_total": int(counters.get("skill_invoke_failure_total", 0)),
                    "validation_error_total": int(counters.get("skill_validation_error_total", 0)),
                    "access_denied_total": int(counters.get("skill_access_denied_total", 0)),
                    "disabled_total": int(counters.get("skill_disabled_total", 0)),
                },
                "by_skill": {
                    "invoke_total": _skill_name_stats("_invoke_total"),
                    "success_total": _skill_name_stats("_success_total"),
                    "failure_total": _skill_name_stats("_failure_total"),
                    "validation_error_total": _skill_name_stats("_validation_error_total"),
                    "access_denied_total": _skill_name_stats("_access_denied_total"),
                },
            },
            "cron": {
                "totals": {
                    "execute_total": int(counters.get("cron_execute_total", 0)),
                    "success_total": int(counters.get("cron_success_total", 0)),
                    "failure_total": int(counters.get("cron_failure_total", 0)),
                    "blocked_total": int(counters.get("cron_blocked_total", 0)),
                },
                "by_job": {
                    "execute_total": _cron_job_stats("_execute_total"),
                    "success_total": _cron_job_stats("_success_total"),
                    "failure_total": _cron_job_stats("_failure_total"),
                    "blocked_total": _cron_job_stats("_blocked_total"),
                },
            },
            "sandbox": {
                "events_total": int(counters.get("sandbox_events_total", 0)),
                "backend": _sandbox_backend_stats(),
                "decision": _sandbox_decision_stats(),
            },
        }


    def history_snapshot(self) -> dict:
        now = time.time()
        with self._lock:
            windows = sorted(set(int(w) for w in self._history_windows if int(w) > 0))
            event_history = list(self._event_history)
            timer_history = list(self._timer_history)

        def _window_event_sum(prefix: str, seconds: int) -> int:
            cutoff = now - seconds
            total = 0.0
            for ts, name, value in event_history:
                if ts >= cutoff and name.startswith(prefix):
                    total += float(value)
            return int(total)

        def _window_exact_sum(name: str, seconds: int) -> int:
            cutoff = now - seconds
            total = 0.0
            for ts, event_name, value in event_history:
                if ts >= cutoff and event_name == name:
                    total += float(value)
            return int(total)

        def _window_timer(name: str, seconds: int) -> dict:
            cutoff = now - seconds
            vals = [float(value) for ts, timer_name, value in timer_history if ts >= cutoff and timer_name == name]
            count = len(vals)
            total = sum(vals)
            return {
                "count": count,
                "sum_s": round(total, 6),
                "avg_s": round((total / count) if count else 0.0, 6),
            }

        def _window_suffix_map(prefix: str, suffix: str, seconds: int) -> dict[str, int]:
            cutoff = now - seconds
            out: dict[str, float] = {}
            for ts, name, value in event_history:
                if ts < cutoff:
                    continue
                if name.startswith(prefix) and name.endswith(suffix):
                    item = name[len(prefix):-len(suffix)] if suffix else name[len(prefix):]
                    out[item] = out.get(item, 0.0) + float(value)
            return {k: int(v) for k, v in sorted(out.items())}

        windows_out = {}
        for seconds in windows:
            key = f"last_{seconds}s"
            windows_out[key] = {
                "http": {
                    "requests_total": _window_exact_sum("http_requests_total", seconds),
                    "status": {
                        "2xx": _window_event_sum("http_status_2", seconds),
                        "4xx": _window_event_sum("http_status_4", seconds),
                        "5xx": _window_event_sum("http_status_5", seconds),
                    },
                    "latency": _window_timer("http_request", seconds),
                    "auth_failed_total": _window_exact_sum("auth_failed_total", seconds),
                    "rate_limited_total": _window_exact_sum("rate_limited_total", seconds),
                },
                "governor": {
                    "evaluations_total": _window_exact_sum("governor_evaluations_total", seconds),
                    "approved_total": _window_exact_sum("governor_decision_approved_total", seconds),
                    "warned_total": _window_exact_sum("governor_decision_warned_total", seconds),
                    "blocked_total": _window_exact_sum("governor_decision_blocked_total", seconds),
                },
                "skills": {
                    "invoke_total": _window_exact_sum("skill_invoke_total", seconds),
                    "success_total": _window_exact_sum("skill_invoke_success_total", seconds),
                    "failure_total": _window_exact_sum("skill_invoke_failure_total", seconds),
                    "validation_error_total": _window_exact_sum("skill_validation_error_total", seconds),
                    "access_denied_total": _window_exact_sum("skill_access_denied_total", seconds),
                    "by_skill": {
                        "invoke_total": _window_suffix_map("skill_", "_invoke_total", seconds),
                        "success_total": _window_suffix_map("skill_", "_success_total", seconds),
                        "failure_total": _window_suffix_map("skill_", "_failure_total", seconds),
                        "validation_error_total": _window_suffix_map("skill_", "_validation_error_total", seconds),
                        "access_denied_total": _window_suffix_map("skill_", "_access_denied_total", seconds),
                    },
                },
                "cron": {
                    "execute_total": _window_exact_sum("cron_execute_total", seconds),
                    "success_total": _window_exact_sum("cron_success_total", seconds),
                    "failure_total": _window_exact_sum("cron_failure_total", seconds),
                    "blocked_total": _window_exact_sum("cron_blocked_total", seconds),
                    "by_job": {
                        "execute_total": _window_suffix_map("cron_job_", "_execute_total", seconds),
                        "success_total": _window_suffix_map("cron_job_", "_success_total", seconds),
                        "failure_total": _window_suffix_map("cron_job_", "_failure_total", seconds),
                        "blocked_total": _window_suffix_map("cron_job_", "_blocked_total", seconds),
                    },
                },
                "sandbox": {
                    "events_total": _window_exact_sum("sandbox_events_total", seconds),
                    "blocked_total": _window_exact_sum("sandbox_decision_BLOCKED_total", seconds),
                    "approved_total": _window_exact_sum("sandbox_decision_APPROVED_total", seconds),
                    "warned_total": _window_exact_sum("sandbox_decision_WARNED_total", seconds),
                    "by_backend": _window_suffix_map("sandbox_backend_", "_total", seconds),
                    "by_decision": _window_suffix_map("sandbox_decision_", "_total", seconds),
                },
            }
        return {"windows": windows_out, "retention": {"max_events": 20000, "max_timers": 20000}}

    def as_prometheus(self) -> str:
        snap = self.snapshot()
        lines: list[str] = []
        lines.append("# HELP archillx_uptime_seconds Process uptime in seconds")
        lines.append("# TYPE archillx_uptime_seconds gauge")
        lines.append(f"archillx_uptime_seconds {snap['uptime_s']}")
        for name, value in sorted(snap["counters"].items()):
            metric = _sanitize(name)
            lines.append(f"# TYPE {metric} counter")
            lines.append(f"{metric} {float(value)}")
        for name, value in sorted(snap["gauges"].items()):
            metric = _sanitize(name)
            lines.append(f"# TYPE {metric} gauge")
            lines.append(f"{metric} {float(value)}")
        for name, stats in sorted(snap["timers"].items()):
            metric = _sanitize(name)
            lines.append(f"# TYPE {metric}_seconds summary")
            lines.append(f"{metric}_seconds_sum {float(stats['sum_s'])}")
            lines.append(f"{metric}_seconds_count {int(stats['count'])}")
            lines.append(f"{metric}_seconds_avg {float(stats['avg_s'])}")
        return "\n".join(lines) + "\n"


def _sanitize(name: str) -> str:
    out = []
    for ch in name:
        out.append(ch if (ch.isalnum() or ch == '_') else '_')
    metric = ''.join(out).strip('_') or 'archillx_metric'
    if not metric.startswith('archillx_'):
        metric = f"archillx_{metric}"
    return metric


telemetry = Telemetry()
