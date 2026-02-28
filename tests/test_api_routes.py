from __future__ import annotations

from app.config import settings


def test_health_returns_ok_and_request_headers(client):
    resp = client.get('/v1/health', headers={'x-request-id': 'req-health-1'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['status'] == 'ok'
    assert body['system'] == 'ArcHillx'
    assert resp.headers['x-request-id'] == 'req-health-1'
    assert 'x-elapsed-ms' in resp.headers


def test_skills_invoke_validation_error(client, monkeypatch):
    from app.runtime import skill_manager as sm_mod

    def boom(name, inputs, context=None):
        raise sm_mod.SkillValidationError('missing required field: code')

    monkeypatch.setattr(sm_mod.skill_manager, 'invoke', boom)
    resp = client.post('/v1/skills/invoke', json={'name': 'code_exec', 'inputs': {}})
    assert resp.status_code == 400
    detail = resp.json()['detail']
    assert detail['code'] == 'SKILL_INPUT_INVALID'
    assert detail['details']['name'] == 'code_exec'


def test_skills_invoke_requires_auth_when_api_key_enabled(client):
    settings.api_key = 'k1'
    settings.admin_token = 'admin1'
    resp = client.post('/v1/skills/invoke', json={'name': 'web_search', 'inputs': {'query': 'test'}})
    assert resp.status_code == 401
    body = resp.json()
    assert body['detail']['code'] == 'UNAUTHORIZED'


def test_memory_search_passes_filters(client, monkeypatch):
    from app.memory import store as store_mod

    captured = {}

    def fake_query(q, top_k=5, tags=None, min_importance=0.0, source=None):
        captured.update({
            'q': q,
            'top_k': top_k,
            'tags': tags,
            'min_importance': min_importance,
            'source': source,
        })
        return [{'id': 1, 'content': 'cron job memory', 'score': 1.2}]

    monkeypatch.setattr(store_mod.memory_store, 'query', fake_query)
    resp = client.get('/v1/memory/search?q=cron&top_k=3&tags=cron,api&min_importance=0.4&source=test')
    assert resp.status_code == 200
    body = resp.json()
    assert body['results'][0]['score'] == 1.2
    assert captured == {
        'q': 'cron',
        'top_k': 3,
        'tags': ['cron', 'api'],
        'min_importance': 0.4,
        'source': 'test',
    }


def test_cron_add_requires_schedule_input(client):
    resp = client.post('/v1/cron', json={'name': 'job1', 'skill_name': 'web_search', 'input_data': {}})
    assert resp.status_code == 400
    detail = resp.json()['detail']
    assert detail['code'] == 'CRON_INPUT_INVALID'


def test_cron_trigger_not_found(client, monkeypatch):
    from app.runtime import cron as cron_mod

    def fake_trigger(name):
        raise KeyError(f'cron not found: {name}')

    monkeypatch.setattr(cron_mod.cron_system, 'trigger_now', fake_trigger)
    resp = client.post('/v1/cron/missing-job/trigger')
    assert resp.status_code == 404
    detail = resp.json()['detail']
    assert detail['code'] == 'CRON_NOT_FOUND'
    assert detail['details']['name'] == 'missing-job'
