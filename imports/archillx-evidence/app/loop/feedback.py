"""
ArcHillx v1.0.0 — Feedback Engine
任務結果學習：寫入記憶 + 本地 JSONL evidence 日誌。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("archillx.feedback")


def _log_dir() -> Path:
    try:
        from ..config import settings
        return Path(settings.evidence_dir) / "logs"
    except Exception:
        return Path("./evidence/logs")


class FeedbackEngine:

    def on_task_success(self, task_id: int, title: str, skill_name: str,
                        output_summary: str, tokens_used: int = 0) -> None:
        content = (f"[ArcHillx] Task SUCCESS — {title}\n"
                   f"Skill: {skill_name} | Tokens: {tokens_used}\n"
                   f"Output: {output_summary[:300]}")
        self._mem(content, tags=["task_success", skill_name],
                  importance=0.6,
                  metadata={"task_id": task_id, "skill": skill_name,
                             "tokens": tokens_used,
                             "ts": datetime.utcnow().isoformat()})
        self._jsonl("task_success", {"task_id": task_id, "title": title,
                                      "skill_name": skill_name,
                                      "tokens_used": tokens_used,
                                      "output_summary": output_summary})
        logger.info("feedback: task %d success", task_id)

    def on_task_failure(self, task_id: int, title: str, skill_name: str,
                        error_msg: str) -> None:
        content = (f"[ArcHillx] Task FAILED — {title}\n"
                   f"Skill: {skill_name}\nError: {error_msg[:300]}")
        self._mem(content, tags=["task_failure", skill_name],
                  importance=0.8,
                  metadata={"task_id": task_id, "skill": skill_name,
                             "error": error_msg,
                             "ts": datetime.utcnow().isoformat()})
        self._jsonl("task_failure", {"task_id": task_id, "title": title,
                                      "skill_name": skill_name,
                                      "error_msg": error_msg})
        logger.info("feedback: task %d failure", task_id)

    def on_governor_blocked(self, action: str, reason: str,
                            context: dict | None = None) -> None:
        self._mem(f"[ArcHillx] Governor BLOCKED — {action}\nReason: {reason}",
                  tags=["governor_blocked"], importance=0.9,
                  metadata={"action": action, "reason": reason})
        self._jsonl("governor_blocked",
                    {"action": action, "reason": reason, "context": context or {}})

    def on_goal_progress(self, goal_id: int, title: str,
                         old: float, new: float, note: str = "") -> None:
        self._mem(f"[ArcHillx] Goal — {title}\n{old:.0%} → {new:.0%}\n{note}",
                  tags=["goal_progress", f"goal:{goal_id}"], importance=0.5)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _mem(self, content: str, tags: list[str] | None = None,
             importance: float = 0.5, metadata: dict | None = None) -> None:
        try:
            from ..memory.store import memory_store
            memory_store.add(content=content, source="archillx",
                             tags=tags, importance=importance,
                             metadata=metadata)
        except Exception as e:
            logger.debug("feedback._mem failed: %s", e)

    def _jsonl(self, event_type: str, data: dict) -> None:
        try:
            log_dir = _log_dir()
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"archillx_{datetime.utcnow():%Y-%m-%d}.jsonl"
            entry = {"ts": datetime.utcnow().isoformat(),
                     "type": event_type, "data": data}
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug("feedback._jsonl failed: %s", e)


feedback = FeedbackEngine()
