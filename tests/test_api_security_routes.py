from __future__ import annotations

from app.config import settings


def test_skills_invoke_acl_denied_for_anonymous_file_ops(client, monkeypatch):
    settings.enable_skill_acl = True
    settings.api_key = ''
    settings.admin_token = ''

    from app.runtime import skill_manager as sm_mod

    def fake_invoke(name, inputs, context=None):
        assert name == 'file_ops'
        assert context['source'] == 'api'
        assert context['role'] == 'anonymous'
        raise sm_mod.SkillAccessDenied('role anonymous not allowed for file_ops')

    monkeypatch.setattr(sm_mod.skill_manager, 'invoke', fake_invoke)
    resp = client.post('/v1/skills/invoke', json={'name': 'file_ops', 'inputs': {'operation': 'exists', 'path': '/tmp'}})
    assert resp.status_code == 400
    body = resp.json()['detail']
    assert body['code'] == 'SKILL_ACCESS_DENIED'
    assert body['details']['name'] == 'file_ops'


def test_skills_invoke_acl_allows_admin_file_ops(client, monkeypatch):
    settings.enable_skill_acl = True
    settings.api_key = 'k1'
    settings.admin_token = 'admin1'

    from app.runtime import skill_manager as sm_mod
    from app.skills.file_ops import run as run_file

    def fake_invoke(name, inputs, context=None):
        assert name == 'file_ops'
        assert context['role'] == 'admin'
        return {'success': True, 'output': run_file(inputs), 'error': None, 'elapsed_s': 0.001}

    monkeypatch.setattr(sm_mod.skill_manager, 'invoke', fake_invoke)
    resp = client.post(
        '/v1/skills/invoke',
        json={'name': 'file_ops', 'inputs': {'operation': 'exists', 'path': '/tmp'}},
        headers={'x-api-key': 'admin1'},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['output']['exists'] is True


def test_skills_invoke_code_exec_disabled_even_for_admin(client, monkeypatch):
    settings.enable_skill_acl = True
    settings.api_key = 'k1'
    settings.admin_token = 'admin1'

    from app.runtime import skill_manager as sm_mod
    from app.skills.code_exec import run as run_code

    def fake_invoke(name, inputs, context=None):
        assert name == 'code_exec'
        assert context['role'] == 'admin'
        return {'success': False, 'output': run_code(inputs), 'error': 'code_exec disabled by policy', 'elapsed_s': 0.001}

    monkeypatch.setattr(sm_mod.skill_manager, 'invoke', fake_invoke)
    resp = client.post(
        '/v1/skills/invoke',
        json={'name': 'code_exec', 'inputs': {'code': 'print(1)'}},
        headers={'x-api-key': 'admin1'},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is False
    assert 'disabled by policy' in body['error']
    assert body['output']['backend'] in ('process', 'docker')


def test_skills_invoke_code_exec_denied_for_api_key_role(client, monkeypatch):
    settings.enable_skill_acl = True
    settings.api_key = 'k1'
    settings.admin_token = 'admin1'

    from app.runtime import skill_manager as sm_mod

    def fake_invoke(name, inputs, context=None):
        assert name == 'code_exec'
        assert context['role'] == 'api_key'
        raise sm_mod.SkillAccessDenied('role api_key not allowed for code_exec')

    monkeypatch.setattr(sm_mod.skill_manager, 'invoke', fake_invoke)
    resp = client.post(
        '/v1/skills/invoke',
        json={'name': 'code_exec', 'inputs': {'code': 'print(1)'}},
        headers={'x-api-key': 'k1'},
    )
    assert resp.status_code == 400
    body = resp.json()['detail']
    assert body['code'] == 'SKILL_ACCESS_DENIED'
    assert body['details']['name'] == 'code_exec'
