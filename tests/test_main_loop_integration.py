from __future__ import annotations

import types
from types import SimpleNamespace

from app.loop.main_loop import LoopInput, main_loop


class TaskRecorder:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(("create", kwargs))
        return 111

    def assign(self, task_id, skill_name, governor_ok=True, model=None):
        self.calls.append(("assign", {"task_id": task_id, "skill_name": skill_name, "governor_ok": governor_ok, "model": model}))

    def start_executing(self, task_id):
        self.calls.append(("start_executing", {"task_id": task_id}))

    def start_verifying(self, task_id):
        self.calls.append(("start_verifying", {"task_id": task_id}))

    def close(self, task_id, output_data, tokens_used):
        self.calls.append(("close", {"task_id": task_id, "output_data": output_data, "tokens_used": tokens_used}))

    def fail(self, task_id, reason):
        self.calls.append(("fail", {"task_id": task_id, "reason": reason}))


class GoalTrackerStub:
    def __init__(self, status="active", progress=0.4):
        self.status = status
        self.progress = progress
        self.update_calls = []

    def list_active(self):
        return [{"id": 1, "status": self.status, "progress": self.progress}]

    def get(self, goal_id):
        return {"id": goal_id, "status": self.status, "progress": self.progress}

    def update_progress(self, goal_id, progress, notes=None):
        self.update_calls.append({"goal_id": goal_id, "progress": progress, "notes": notes})


class FeedbackStub:
    def __init__(self):
        self.calls = []

    def on_task_success(self, *args):
        self.calls.append(("success", args))

    def on_task_failure(self, *args):
        self.calls.append(("failure", args))

    def on_governor_blocked(self, **kwargs):
        self.calls.append(("blocked", kwargs))


def install_main_loop_fakes(monkeypatch, install_module, *, is_registered=True,
                            invoke_result=None, governor_decision="APPROVED",
                            goal_status="active", model_name="provider/model-a",
                            complete_result=None):
    tasks = TaskRecorder()
    feedback = FeedbackStub()
    goals = GoalTrackerStub(status=goal_status)
    invoke_calls = []
    select_calls = []
    complete_calls = []

    fake_lifecycle_mod = types.ModuleType("app.runtime.lifecycle")
    fake_lifecycle_mod.lifecycle = SimpleNamespace(tasks=tasks)
    install_module("app.runtime.lifecycle", fake_lifecycle_mod)

    def fake_invoke(name, inputs, context=None):
        invoke_calls.append({"name": name, "inputs": inputs, "context": context})
        return invoke_result or {"success": True, "output": {"ok": True}, "tokens": 7, "error": None}

    fake_skill_mod = types.ModuleType("app.runtime.skill_manager")
    fake_skill_mod.skill_manager = SimpleNamespace(
        is_registered=lambda name: is_registered,
        invoke=fake_invoke,
    )
    install_module("app.runtime.skill_manager", fake_skill_mod)

    def fake_select_model(task_type, budget):
        select_calls.append({"task_type": task_type, "budget": budget})
        return model_name, {"provider": "x"}

    def fake_complete(**kwargs):
        complete_calls.append(kwargs)
        result = complete_result or SimpleNamespace(content="direct answer", total_tokens=33)
        return result

    fake_router_mod = types.ModuleType("app.utils.model_router")
    fake_router_mod.model_router = SimpleNamespace(
        select_model=fake_select_model,
        complete=fake_complete,
    )
    install_module("app.utils.model_router", fake_router_mod)

    fake_gov_mod = types.ModuleType("app.governor.governor")
    fake_gov_mod.governor = SimpleNamespace(
        evaluate=lambda **kwargs: SimpleNamespace(
            decision=governor_decision,
            reason="policy block" if governor_decision == "BLOCKED" else "ok",
        )
    )
    install_module("app.governor.governor", fake_gov_mod)

    fake_mem_mod = types.ModuleType("app.memory.store")
    fake_mem_mod.memory_store = SimpleNamespace(
        query=lambda query, top_k=3, tags=None: [{"id": 1, "content": f"mem:{query}", "tags": tags or []}]
    )
    install_module("app.memory.store", fake_mem_mod)

    fake_goal_mod = types.ModuleType("app.loop.goal_tracker")
    fake_goal_mod.goal_tracker = goals
    install_module("app.loop.goal_tracker", fake_goal_mod)

    fake_feedback_mod = types.ModuleType("app.loop.feedback")
    fake_feedback_mod.feedback = feedback
    install_module("app.loop.feedback", fake_feedback_mod)

    return {
        "tasks": tasks,
        "feedback": feedback,
        "goals": goals,
        "invoke_calls": invoke_calls,
        "select_calls": select_calls,
        "complete_calls": complete_calls,
    }


def test_main_loop_registered_skill_success_updates_goal(monkeypatch, install_module):
    env = install_main_loop_fakes(monkeypatch, install_module, is_registered=True)

    result = main_loop.run(LoopInput(
        command="search release notes",
        session_id=55,
        goal_id=9,
        task_type="web_search",
        budget="high",
        context={"lang": "zh"},
    ))

    assert result.success is True
    assert result.task_id == 111
    assert result.skill_used == "web_search"
    assert result.model_used == "provider/model-a"
    assert result.tokens_used == 7
    assert env["invoke_calls"][0]["name"] == "web_search"
    assert env["invoke_calls"][0]["inputs"]["command"] == "search release notes"
    assert env["invoke_calls"][0]["inputs"]["lang"] == "zh"
    assert env["invoke_calls"][0]["context"] == {
        "source": "agent", "role": "system", "session_id": 55, "task_id": 111
    }
    assert env["select_calls"] == [{"task_type": "web_search", "budget": "high"}]
    assert env["goals"].update_calls[0]["goal_id"] == 9
    assert env["goals"].update_calls[0]["progress"] == 0.5
    assert [c[0] for c in env["tasks"].calls] == [
        "create", "assign", "start_executing", "start_verifying", "close"
    ]


def test_main_loop_skill_hint_overrides_and_governor_blocked(monkeypatch, install_module):
    env = install_main_loop_fakes(
        monkeypatch,
        install_module,
        governor_decision="BLOCKED",
    )

    result = main_loop.run(LoopInput(
        command="search docs but use files",
        skill_hint="file_ops",
        task_type="web_search",
    ))

    assert result.success is False
    assert result.governor_approved is False
    assert result.skill_used == "file_ops"
    assert "Governor blocked" in result.error
    assert env["invoke_calls"] == []
    assert env["feedback"].calls[0][0] == "blocked"
    assert env["tasks"].calls[-1][0] == "fail"
    assert env["tasks"].calls[-1][1]["reason"] == "governor_blocked: policy block"


def test_main_loop_unregistered_skill_falls_back_to_model_direct(monkeypatch, install_module):
    env = install_main_loop_fakes(monkeypatch, install_module, is_registered=False)

    result = main_loop.run(LoopInput(
        command="please browse latest docs",
        task_type="web_search",
        budget="low",
    ))

    assert result.success is True
    assert result.skill_used == "_model_direct"
    assert result.output == "direct answer"
    assert result.tokens_used == 33
    assert env["invoke_calls"] == []
    assert env["complete_calls"][0]["prompt"].startswith("please browse latest docs")
    assert env["complete_calls"][0]["task_type"] == "web_search"
    assert env["tasks"].calls[-1][0] == "close"
    assert env["tasks"].calls[-1][1]["tokens_used"] == 33


def test_main_loop_skill_error_marks_task_failed(monkeypatch, install_module):
    env = install_main_loop_fakes(
        monkeypatch,
        install_module,
        invoke_result={"success": False, "output": None, "tokens": 4, "error": "tool crashed"},
        goal_status="paused",
    )

    result = main_loop.run(LoopInput(
        command="write file",
        task_type="file_ops",
        goal_id=77,
    ))

    assert result.success is False
    assert result.skill_used == "file_ops"
    assert result.error == "tool crashed"
    assert result.tokens_used == 4
    assert env["tasks"].calls[-1][0] == "fail"
    assert env["tasks"].calls[-1][1]["reason"] == "tool crashed"
    assert env["feedback"].calls[0][0] == "failure"
    assert env["goals"].update_calls == []
