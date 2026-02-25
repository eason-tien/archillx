"""
ArcHillx v1.0.0 — Lightweight Governor
規則型風險評估，不依賴外部 LMF 或複雜 ML 模型。
模式：soft_block | hard_block | audit_only | off
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger("archillx.governor")

# ── 高風險行為關鍵字 ─────────────────────────────────────────────────────────

_HIGH_RISK_ACTIONS = {
    "delete", "rm ", "rmdir", "drop table", "truncate",
    "format", "shutdown", "reboot", "kill", "terminate",
    "exec(", "eval(", "__import__",
}

_MEDIUM_RISK_ACTIONS = {
    "write", "modify", "update", "patch", "post",
    "send", "deploy", "push", "publish",
    "code_exec", "subprocess",
}

_SENSITIVE_PATHS = {
    "/etc/", "/usr/", "/bin/", "/sbin/",
    "~/.ssh", "~/.config", "/root/",
}


@dataclass
class GovDecision:
    decision: str          # APPROVED | WARNED | BLOCKED
    risk_score: int        # 0–100
    reason: str
    action: str
    context: dict


class Governor:
    """
    輕量 Governor — 同步風險評估。

    Modes:
      off          → 永遠 APPROVED（開發用）
      audit_only   → 記錄但不阻擋
      soft_block   → 高風險 WARNED，超閾值 BLOCKED
      hard_block   → 嚴格阻擋，風險 > warn 即 BLOCKED
    """

    def __init__(self):
        from ..config import settings
        self.mode = settings.governor_mode
        self.block_threshold = settings.risk_block_threshold
        self.warn_threshold = settings.risk_warn_threshold

    def evaluate(self, action: str,
                 context: dict | None = None) -> GovDecision:
        ctx = context or {}

        if self.mode == "off":
            return GovDecision("APPROVED", 0, "governor_off", action, ctx)

        score = self._score(action, ctx)
        decision, reason = self._decide(score)

        self._log(action, decision, score, reason, ctx)

        return GovDecision(decision=decision, risk_score=score,
                           reason=reason, action=action, context=ctx)

    def _score(self, action: str, ctx: dict) -> int:
        score = 0
        action_lower = action.lower()
        ctx_str = json.dumps(ctx).lower()

        for kw in _HIGH_RISK_ACTIONS:
            if kw in action_lower or kw in ctx_str:
                score += 35
                break

        for kw in _MEDIUM_RISK_ACTIONS:
            if kw in action_lower:
                score += 20
                break

        for sp in _SENSITIVE_PATHS:
            if sp in ctx_str:
                score += 30
                break

        # Cron / background source: lower trust
        if ctx.get("source") == "cron":
            score += 10

        # Skill-specific risk
        skill = ctx.get("skill", "")
        if skill == "code_exec":
            score += 25
        elif skill == "file_ops":
            op = ctx.get("operation", "")
            if op in ("delete", "write"):
                score += 20

        return min(score, 100)

    def _decide(self, score: int) -> tuple[str, str]:
        if self.mode == "audit_only":
            return "APPROVED", f"audit_only (score={score})"

        if score >= self.block_threshold:
            if self.mode in ("soft_block", "hard_block"):
                return "BLOCKED", f"risk_score={score} >= block_threshold={self.block_threshold}"
            return "WARNED", f"risk_score={score} (audit_only mode)"

        if score >= self.warn_threshold:
            if self.mode == "hard_block":
                return "BLOCKED", f"risk_score={score} >= warn_threshold={self.warn_threshold} (hard_block)"
            return "WARNED", f"risk_score={score} — proceed with caution"

        return "APPROVED", f"risk_score={score} — ok"

    def _log(self, action: str, decision: str, score: int,
             reason: str, ctx: dict) -> None:
        try:
            from ..db.schema import AHAuditLog, get_db
            db = next(get_db())
            db.add(AHAuditLog(
                action=action[:256],
                decision=decision,
                risk_score=score,
                reason=reason,
                context=json.dumps(ctx),
            ))
            db.commit()
        except Exception as e:
            logger.debug("audit_log write failed: %s", e)

        log_fn = logger.warning if decision != "APPROVED" else logger.debug
        log_fn("Governor %s: action=%s score=%d reason=%s",
               decision, action[:80], score, reason)


governor = Governor()
