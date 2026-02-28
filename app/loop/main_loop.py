"""
ArcHillx v1.0.0 — OODA Main Loop
Observe → Orient → Decide → Act → Learn
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("archillx.main_loop")


@dataclass
class LoopInput:
    command: str
    source: str = "user"               # user | cron | proactive | api
    session_id: int | None = None
    goal_id: int | None = None
    context: dict = field(default_factory=dict)
    skill_hint: str | None = None
    task_type: str = "general"
    budget: str = "medium"


@dataclass
class LoopResult:
    success: bool
    task_id: int | None
    skill_used: str | None
    model_used: str | None
    output: Any
    tokens_used: int
    elapsed_s: float
    governor_approved: bool
    error: str | None = None
    memory_hits: list = field(default_factory=list)


class MainLoop:

    def run(self, inp: LoopInput) -> LoopResult:
        from ..runtime.lifecycle import lifecycle
        from ..runtime.skill_manager import skill_manager
        from ..utils.model_router import model_router
        from ..governor.governor import governor
        from ..memory.store import memory_store
        from .goal_tracker import goal_tracker
        from .feedback import feedback

        t0 = time.monotonic()
        task_id = model_used = skill_used = None
        governor_approved = False
        memory_hits: list = []
        tokens_used = 0

        try:
            # ── 1. OBSERVE ───────────────────────────────────────────────────
            logger.info("[OBSERVE] cmd=%.80s source=%s", inp.command, inp.source)
            task_id = lifecycle.tasks.create(
                title=inp.command[:200],
                task_type=inp.task_type,
                session_id=inp.session_id,
                input_data={"command": inp.command, "context": inp.context},
            )

            # ── 2. ORIENT ────────────────────────────────────────────────────
            logger.info("[ORIENT] querying memory...")
            memory_hits = memory_store.query(inp.command, top_k=3,
                                              tags=["archillx"])
            active_goals = goal_tracker.list_active()

            # ── 3. DECIDE ────────────────────────────────────────────────────
            logger.info("[DECIDE] routing + governor...")
            skill_name = inp.skill_hint or self._pick_skill(inp.command,
                                                             inp.task_type)
            try:
                chosen_model, _ = model_router.select_model(inp.task_type,
                                                             inp.budget)
                model_used = chosen_model
            except Exception:
                model_used = "none"

            # Governor audit
            dec = governor.evaluate(
                action=f"execute_skill:{skill_name}",
                context={"command": inp.command[:300], "skill": skill_name,
                         "source": inp.source, "task_id": task_id},
            )

            if dec.decision == "BLOCKED":
                feedback.on_governor_blocked(
                    action=f"execute_skill:{skill_name}",
                    reason=dec.reason,
                )
                lifecycle.tasks.fail(task_id, f"governor_blocked: {dec.reason}")
                return LoopResult(
                    success=False, task_id=task_id,
                    skill_used=skill_name, model_used=model_used,
                    output=None, tokens_used=0,
                    elapsed_s=round(time.monotonic() - t0, 3),
                    governor_approved=False,
                    error=f"Governor blocked: {dec.reason}",
                )

            governor_approved = True
            lifecycle.tasks.assign(task_id, skill_name,
                                   governor_ok=True, model=model_used)

            # ── 4. ACT ───────────────────────────────────────────────────────
            logger.info("[ACT] skill=%s", skill_name)
            lifecycle.tasks.start_executing(task_id)

            if skill_name == "_model_direct" or not skill_manager.is_registered(
                    skill_name):
                skill_result = self._model_direct(inp, memory_hits, model_router)
                skill_name = "_model_direct"
            else:
                skill_result = skill_manager.invoke(skill_name, {
                    **inp.context, "command": inp.command}, context={"source": "agent", "role": "system", "session_id": inp.session_id, "task_id": task_id})

            skill_used = skill_name
            tokens_used = int(skill_result.get("tokens", 0) or 0)
            lifecycle.tasks.start_verifying(task_id)

            # ── 5. LEARN ─────────────────────────────────────────────────────
            output = skill_result.get("output")
            error = skill_result.get("error")

            if skill_result.get("success", True) and not error:
                lifecycle.tasks.close(task_id, {"output": output}, tokens_used)
                feedback.on_task_success(
                    task_id, inp.command[:100], skill_name,
                    str(output)[:200] if output else "", tokens_used,
                )
                if inp.goal_id:
                    g = goal_tracker.get(inp.goal_id)
                    if g and g["status"] == "active":
                        goal_tracker.update_progress(
                            inp.goal_id, min(g["progress"] + 0.1, 0.99))
            else:
                lifecycle.tasks.fail(task_id, error or "unknown")
                feedback.on_task_failure(
                    task_id, inp.command[:100], skill_name, error or "unknown")

            return LoopResult(
                success=not bool(error),
                task_id=task_id, skill_used=skill_used, model_used=model_used,
                output=output, tokens_used=tokens_used,
                elapsed_s=round(time.monotonic() - t0, 3),
                governor_approved=governor_approved, error=error,
                memory_hits=memory_hits,
            )

        except Exception as e:
            logger.exception("OODA unhandled: %s", e)
            if task_id:
                try:
                    from ..runtime.lifecycle import lifecycle
                    lifecycle.tasks.fail(task_id, str(e))
                except Exception:
                    pass
            return LoopResult(
                success=False, task_id=task_id,
                skill_used=skill_used, model_used=model_used,
                output=None, tokens_used=0,
                elapsed_s=round(time.monotonic() - t0, 3),
                governor_approved=governor_approved, error=str(e),
            )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pick_skill(self, cmd: str, task_type: str) -> str:
        _map = {"web_search": "web_search", "file_ops": "file_ops",
                "code_exec": "code_exec"}
        if task_type in _map:
            return _map[task_type]
        c = cmd.lower()
        if any(w in c for w in ["search", "find", "look up", "搜尋", "查"]):
            return "web_search"
        if any(w in c for w in ["file", "read", "write", "list", "檔案"]):
            return "file_ops"
        if any(w in c for w in ["code", "run", "execute", "python", "執行"]):
            return "code_exec"
        return "_model_direct"

    def _model_direct(self, inp: LoopInput, hits: list, router) -> dict:
        mem_ctx = ""
        if hits:
            mem_ctx = "\n\n## Related Memory:\n" + "\n".join(
                f"- {h.get('content', '')[:100]}" for h in hits)
        try:
            resp = router.complete(
                prompt=f"{inp.command}{mem_ctx}",
                system="You are ArcHillx, an autonomous AI assistant.",
                task_type=inp.task_type, budget=inp.budget,
            )
            return {"success": True, "output": resp.content,
                    "tokens": resp.total_tokens, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}


main_loop = MainLoop()
