from __future__ import annotations

from types import SimpleNamespace

from app.config import settings



def test_agent_run_success_exposes_model_alias_and_headers(client, monkeypatch):
    from app.loop import main_loop as loop_mod

    def fake_run(loop_input):
        assert loop_input.command == 'search docs'
        assert loop_input.source == 'user'
        assert loop_input.session_id == 42
        return SimpleNamespace(
            success=True,
            task_id=101,
            skill_used='web_search',
            model_used='provider/model-x',
            output={'answer': 'ok'},
            tokens_used=123,
            elapsed_s=0.42,
            governor_approved=True,
            error=None,
            memory_hits=[{'id': 1, 'content': 'doc'}],
        )

    monkeypatch.setattr(loop_mod.main_loop, 'run', fake_run)
    resp = client.post(
        '/v1/agent/run',
        json={'command': 'search docs', 'session_id': 42},
        headers={'x-request-id': 'req-agent-1'},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['task_id'] == 101
    assert body['skill_used'] == 'web_search'
    assert body['model_used'] == 'provider/model-x'
    assert body['tokens_used'] == 123
    assert body['memory_hits'][0]['id'] == 1
    assert resp.headers['x-request-id'] == 'req-agent-1'
    assert 'x-elapsed-ms' in resp.headers



def test_agent_run_governor_blocked_shape(client, monkeypatch):
    from app.loop import main_loop as loop_mod

    def fake_run(loop_input):
        assert loop_input.skill_hint == 'file_ops'
        return SimpleNamespace(
            success=False,
            task_id=77,
            skill_used='file_ops',
            model_used='provider/model-safe',
            output=None,
            tokens_used=0,
            elapsed_s=0.05,
            governor_approved=False,
            error='Governor blocked: risky filesystem action',
            memory_hits=[],
        )

    monkeypatch.setattr(loop_mod.main_loop, 'run', fake_run)
    resp = client.post('/v1/agent/run', json={
        'command': 'read system file',
        'skill_hint': 'file_ops',
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is False
    assert body['governor_approved'] is False
    assert body['task_id'] == 77
    assert body['model_used'] == 'provider/model-safe'
    assert 'Governor blocked' in body['error']



def test_agent_run_internal_failure_returns_structured_500(client, monkeypatch):
    from app.loop import main_loop as loop_mod

    def fake_run(_loop_input):
        raise RuntimeError('router offline')

    monkeypatch.setattr(loop_mod.main_loop, 'run', fake_run)
    resp = client.post('/v1/agent/run', json={'command': 'run this'})
    assert resp.status_code == 500
    detail = resp.json()['detail']
    assert detail['code'] == 'AGENT_RUN_FAILED'
    assert detail['message'] == 'Agent execution failed'
    assert detail['details']['reason'] == 'router offline'



def test_agent_run_requires_api_key_when_enabled(client):
    settings.api_key = 'k-test'
    settings.admin_token = 'admin-test'
    resp = client.post('/v1/agent/run', json={'command': 'hi'})
    assert resp.status_code == 401
    detail = resp.json()['detail']
    assert detail['code'] == 'UNAUTHORIZED'



def test_agent_run_accepts_admin_token_when_auth_enabled(client, monkeypatch):
    from app.loop import main_loop as loop_mod

    settings.api_key = 'k-test'
    settings.admin_token = 'admin-test'

    def fake_run(loop_input):
        assert loop_input.command == 'secure run'
        return SimpleNamespace(
            success=True,
            task_id=900,
            skill_used='_model_direct',
            model_used='provider/model-admin',
            output='ok',
            tokens_used=11,
            elapsed_s=0.11,
            governor_approved=True,
            error=None,
            memory_hits=[],
        )

    monkeypatch.setattr(loop_mod.main_loop, 'run', fake_run)
    resp = client.post(
        '/v1/agent/run',
        json={'command': 'secure run'},
        headers={'x-api-key': 'admin-test'},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['task_id'] == 900
    assert body['model_used'] == 'provider/model-admin'



def test_agent_run_validation_error_includes_request_id(client):
    resp = client.post('/v1/agent/run', json={'source': 'user'}, headers={'x-request-id': 'req-missing-command'})
    assert resp.status_code == 422
    detail = resp.json()['detail']
    assert detail['code'] == 'REQUEST_VALIDATION_FAILED'
    assert detail['request_id'] == 'req-missing-command'
    assert any(err['loc'][-1] == 'command' for err in detail['errors'])
