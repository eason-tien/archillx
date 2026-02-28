from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import pstdev
from typing import Any
from urllib.request import Request, urlopen

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
        self._last_alert_ts: float = 0.0

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

    def _entropy_ops_db_path(self) -> Path:
        p = Path(settings.entropy_ops_sqlite_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _ensure_entropy_ops_index(self) -> None:
        db_path = self._entropy_ops_db_path()
        con = sqlite3.connect(str(db_path))
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS entropy_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    state TEXT,
                    risk TEXT,
                    score REAL,
                    action TEXT,
                    event TEXT,
                    sha256_line TEXT UNIQUE,
                    raw_path TEXT
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS ix_entropy_events_ts ON entropy_events(ts)")
            con.execute("CREATE INDEX IF NOT EXISTS ix_entropy_events_event ON entropy_events(event)")
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS entropy_proposals (
                    proposal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_ts REAL NOT NULL,
                    state TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    score REAL NOT NULL,
                    vector_json TEXT NOT NULL,
                    action_hint TEXT,
                    status TEXT NOT NULL,
                    approved_by TEXT,
                    approved_ts REAL,
                    decision_reason TEXT,
                    executed_action TEXT,
                    result_json TEXT
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS ix_entropy_proposals_status ON entropy_proposals(status)")
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS entropy_alert_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    dedup_key TEXT UNIQUE NOT NULL,
                    risk TEXT,
                    state TEXT,
                    score REAL
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS ix_entropy_alert_log_ts ON entropy_alert_log(ts)")
            con.commit()
        finally:
            con.close()

    def _index_evidence_line(self, payload: dict[str, Any], line_hash: str) -> None:
        try:
            self._ensure_entropy_ops_index()
            db_path = self._entropy_ops_db_path()
            con = sqlite3.connect(str(db_path))
            try:
                ts_raw = payload.get('timestamp') or payload.get('ts')
                ts = datetime.fromisoformat(str(ts_raw)).timestamp() if ts_raw else time.time()
                event = payload.get('event') or 'tick'
                actions = payload.get('triggered_action')
                action = json.dumps(actions, ensure_ascii=False) if isinstance(actions, list) else (str(actions) if actions is not None else None)
                con.execute(
                    'INSERT OR IGNORE INTO entropy_events(ts,state,risk,score,action,event,sha256_line,raw_path) VALUES(?,?,?,?,?,?,?,?)',
                    (
                        float(ts),
                        str(payload.get('state') or ''),
                        str(payload.get('risk') or payload.get('risk_level') or ''),
                        float(payload.get('score') or payload.get('entropy_score') or 0.0),
                        action,
                        str(event),
                        line_hash,
                        str(self._evidence_path()),
                    ),
                )
                con.commit()
            finally:
                con.close()
        except Exception:
            pass

    def _bucket_start(self, ts: float, seconds: int) -> int:
        s = max(1, int(seconds))
        return int(ts // s) * s

    def _top_cause(self, vector: dict[str, float]) -> str:
        return max(vector.items(), key=lambda kv: kv[1])[0] if vector else "unknown"

    def _action_hint(self, risk: str, actions: list[str]) -> str:
        if risk == "WARN":
            return "Observe trend and validate entropy tick cadence."
        if risk == "DEGRADED":
            return "Review task backlog/model fallback and apply low-risk stabilizations."
        if risk == "CRITICAL":
            return "Prepare controlled recovery plan and governor approval before execution."
        return "No action needed."

    def _recovery_condition(self) -> str:
        return "Return to NORMAL or RECOVERY state for 2 consecutive ticks."

    def _runbook_ref(self, risk: str) -> str:
        return f"docs/ENTROPY_ALERT_RUNBOOK.md#{risk.lower()}"

    def _alert_dedup_key(self, snap: dict[str, Any], now: float) -> str:
        risk = str(snap.get('risk') or 'NORMAL')
        state = str(snap.get('state') or 'UNKNOWN')
        vector = snap.get('vector') or {}
        top = self._top_cause(vector if isinstance(vector, dict) else {})
        bucket_start = self._bucket_start(now, max(60, int(getattr(settings, 'entropy_alert_cooldown_s', 300))))
        raw = f"{state}|{risk}|{bucket_start}|{top}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def _alert_dedup_exists(self, dedup_key: str, cooldown: int) -> bool:
        try:
            self._ensure_entropy_ops_index()
            con = sqlite3.connect(str(self._entropy_ops_db_path()))
            try:
                cutoff = time.time() - max(0, int(cooldown))
                row = con.execute('SELECT 1 FROM entropy_alert_log WHERE dedup_key = ? AND ts >= ? LIMIT 1', (dedup_key, cutoff)).fetchone()
                return row is not None
            finally:
                con.close()
        except Exception:
            return False

    def _record_alert_log(self, dedup_key: str, snap: dict[str, Any]) -> None:
        try:
            self._ensure_entropy_ops_index()
            con = sqlite3.connect(str(self._entropy_ops_db_path()))
            try:
                con.execute('INSERT OR IGNORE INTO entropy_alert_log(ts,dedup_key,risk,state,score) VALUES(?,?,?,?,?)', (time.time(), dedup_key, str(snap.get('risk') or ''), str(snap.get('state') or ''), float(snap.get('score') or 0.0)))
                con.commit()
            finally:
                con.close()
        except Exception:
            pass

    def _create_proposal_if_needed(self, snap: dict[str, Any]) -> None:
        risk = str(snap.get('risk') or 'NORMAL')
        if risk not in {'CRITICAL', 'DEGRADED'}:
            return
        state = str(snap.get('state') or '')
        score = float(snap.get('score') or 0.0)
        if risk == 'DEGRADED' and score < max(0.6, float(getattr(settings, 'entropy_threshold_degraded', 0.7)) - 0.05):
            return
        try:
            self._ensure_entropy_ops_index()
            con = sqlite3.connect(str(self._entropy_ops_db_path()))
            try:
                open_pending = con.execute('SELECT proposal_id FROM entropy_proposals WHERE status = ? LIMIT 1', ('PENDING',)).fetchone()
                if open_pending:
                    return
                con.execute(
                    'INSERT INTO entropy_proposals(created_ts,state,risk,score,vector_json,action_hint,status) VALUES(?,?,?,?,?,?,?)',
                    (time.time(), state, risk, score, json.dumps(snap.get('vector') or {}, ensure_ascii=False), self._action_hint(risk, snap.get('triggered_action') or []), 'PENDING')
                )
                con.commit()
            finally:
                con.close()
        except Exception:
            pass

    def list_proposals(self, status: str = 'PENDING', limit: int = 50) -> list[dict[str, Any]]:
        self._ensure_entropy_ops_index()
        con = sqlite3.connect(str(self._entropy_ops_db_path()))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute('SELECT * FROM entropy_proposals WHERE (? = "all" OR status = ?) ORDER BY proposal_id DESC LIMIT ?', (status.lower(), status.upper(), max(1, int(limit)))).fetchall()
            out=[]
            for r in rows:
                d=dict(r)
                try:
                    d['vector']=json.loads(d.get('vector_json') or '{}')
                except Exception:
                    d['vector']={}
                out.append(d)
            return out
        finally:
            con.close()

    def set_proposal_decision(self, proposal_id: int, action: str, actor: str, reason: str | None = None) -> dict[str, Any]:
        self._ensure_entropy_ops_index()
        con = sqlite3.connect(str(self._entropy_ops_db_path()))
        con.row_factory = sqlite3.Row
        try:
            row = con.execute('SELECT * FROM entropy_proposals WHERE proposal_id = ?', (int(proposal_id),)).fetchone()
            if not row:
                return {'ok': False, 'error': 'PROPOSAL_NOT_FOUND'}
            status = 'APPROVED' if action == 'approve' else 'REJECTED'
            con.execute('UPDATE entropy_proposals SET status=?, approved_by=?, approved_ts=?, decision_reason=? WHERE proposal_id=?', (status, actor, time.time(), reason, int(proposal_id)))
            con.commit()
            row2 = con.execute('SELECT * FROM entropy_proposals WHERE proposal_id = ?', (int(proposal_id),)).fetchone()
            return {'ok': True, 'proposal': dict(row2)}
        finally:
            con.close()

    def execute_approved_proposal(self, proposal_id: int, actor: str = 'entropy-governor') -> dict[str, Any]:
        from ..recovery.takeover_lock import build_lock_provider, RedisLockProvider
        self._ensure_entropy_ops_index()
        con = sqlite3.connect(str(self._entropy_ops_db_path()))
        con.row_factory = sqlite3.Row
        try:
            row = con.execute('SELECT * FROM entropy_proposals WHERE proposal_id = ?', (int(proposal_id),)).fetchone()
            if not row:
                return {'ok': False, 'error': 'PROPOSAL_NOT_FOUND'}
            if str(row['status']) != 'APPROVED':
                return {'ok': False, 'error': 'PROPOSAL_NOT_APPROVED'}
            provider = build_lock_provider()
            owner = f'entropy-exec:{actor}:{int(time.time())}'
            handle = provider.acquire(owner, settings.recovery_lock_ttl_s) if isinstance(provider, RedisLockProvider) else provider.acquire(owner)
            if not handle:
                return {'ok': False, 'error': 'TAKEOVER_LOCK_FAILED'}
            try:
                executed_action = str(row['action_hint'] or 'Entropy stabilization proposal acknowledged')
                result = {'status': 'executed', 'note': 'manual-governed execution placeholder'}
                con.execute('UPDATE entropy_proposals SET status=?, executed_action=?, result_json=? WHERE proposal_id=?', ('EXECUTED', executed_action, json.dumps(result, ensure_ascii=False), int(proposal_id)))
                con.commit()
                self._append_evidence({'event': 'proposal_execute', 'timestamp': _utcnow().isoformat(), 'proposal_id': int(proposal_id), 'approved_by': row['approved_by'], 'approved_ts': row['approved_ts'], 'executed_action': executed_action, 'result': result})
                return {'ok': True, 'proposal_id': int(proposal_id), 'executed_action': executed_action, 'result': result}
            finally:
                if isinstance(provider, RedisLockProvider):
                    provider.release(owner)
                else:
                    provider.release()
        finally:
            con.close()

    def _append_evidence(self, payload: dict[str, Any]) -> None:
        out = self._evidence_path()
        line_txt = json.dumps(payload, ensure_ascii=False) + "\n"
        line = line_txt.encode("utf-8")
        line_hash = hashlib.sha256(line).hexdigest()
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
        self._index_evidence_line(payload, line_hash)

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

    def _send_alert_if_needed(self, snap: dict[str, Any]) -> None:
        level = str(snap.get('risk') or 'NORMAL')
        if level not in {'WARN', 'DEGRADED', 'CRITICAL'}:
            return
        url = str(getattr(settings, 'entropy_alert_webhook_url', '') or '').strip()
        if not url:
            return
        now = time.time()
        cooldown = max(0, int(getattr(settings, 'entropy_alert_cooldown_s', 300)))
        dedup_key = self._alert_dedup_key(snap, now)
        if self._alert_dedup_exists(dedup_key, cooldown):
            return
        payload = {
            'score': snap.get('score'),
            'state': snap.get('state'),
            'risk': snap.get('risk'),
            'vector': snap.get('vector'),
            'action_hint': self._action_hint(level, snap.get('triggered_action') or []),
            'recovery_condition': self._recovery_condition(),
            'runbook_ref': self._runbook_ref(level),
            'last_transition_ts': snap.get('ts'),
            'report_ref': str(self._evidence_path()),
            'dedup_key': dedup_key,
        }
        try:
            req = Request(url=url, method='POST', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urlopen(req, timeout=3):
                pass
            self._record_alert_log(dedup_key, snap)
            self._last_alert_ts = now
        except Exception:
            return

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
            self._create_proposal_if_needed(snap)
            self._send_alert_if_needed(snap)
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
