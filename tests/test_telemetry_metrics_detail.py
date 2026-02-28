from __future__ import annotations

from app.config import settings
from app.utils.telemetry import telemetry


def test_metrics_include_skill_governor_cron_and_sandbox_families(client, monkeypatch):
    settings.enable_metrics = True
    settings.enable_skill_acl = True
    settings.enable_skill_validation = True
    telemetry.reset()

    from app.governor.governor import governor
    governor.mode = "soft_block"
    governor.evaluate("code_exec", {"skill": "code_exec", "source": "cron"})

    from app.runtime.skill_manager import skill_manager
    skill_manager.register("metric_ok", lambda inputs: {"ok": True}, {"name": "metric_ok"})
    skill_manager.register("metric_fail", lambda inputs: {"error": "boom"}, {"name": "metric_fail"})
    skill_manager.invoke("metric_ok", {})
    skill_manager.invoke("metric_fail", {})

    def _raise(_inputs):
        raise RuntimeError("nope")
    skill_manager.register("metric_raise", _raise, {"name": "metric_raise"})
    skill_manager.invoke("metric_raise", {})

    skill_manager.register("metric_validated", lambda inputs: {"ok": True}, {"name": "metric_validated", "inputs": [{"name": "code", "required": True}]})
    try:
        skill_manager.invoke("metric_validated", {})
    except Exception:
        pass

    skill_manager.register("metric_acl", lambda inputs: {"ok": True}, {"name": "metric_acl", "permissions": ["exec"], "acl": {"allow_roles": ["admin"]}})
    try:
        skill_manager.invoke("metric_acl", {}, context={"source": "api", "role": "anonymous"})
    except Exception:
        pass

    monkeypatch.setenv("ARCHILLX_ENABLE_CODE_EXEC", "true")
    monkeypatch.setenv("ARCHILLX_SANDBOX_BACKEND", "process")
    from app.skills import code_exec
    out = code_exec.run({"code": "print(7)"})
    assert out["success"] is True

    from app.runtime.cron import cron_system
    ok = cron_system._execute("metric_ok", {}, False, job_name="job-ok")
    bad = cron_system._execute("metric_fail", {}, False, job_name="job-bad")
    assert ok["success"] is True
    assert bad["success"] is False

    resp = client.get('/v1/metrics')
    assert resp.status_code == 200
    text = resp.text
    assert 'archillx_governor_evaluations_total' in text
    assert 'archillx_governor_decision_blocked_total' in text
    assert 'archillx_skill_invoke_total' in text
    assert 'archillx_skill_metric_ok_success_total' in text
    assert 'archillx_skill_metric_fail_failure_total' in text
    assert 'archillx_skill_validation_error_total' in text
    assert 'archillx_skill_access_denied_total' in text
    assert 'archillx_cron_execute_total' in text
    assert 'archillx_cron_success_total' in text
    assert 'archillx_cron_failure_total' in text
    assert 'archillx_sandbox_events_total' in text
    assert 'archillx_sandbox_sandbox_execute_done_total' in text
    assert 'archillx_sandbox_backend_process_total' in text
