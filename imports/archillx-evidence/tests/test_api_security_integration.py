from __future__ import annotations

import os
from textwrap import dedent

from app.config import settings


def _manifest() -> str:
    return dedent(
        '''
        version: "1.0"
        skills:
          - name: file_ops
            module: file_ops.py
            handler: run
            permissions: [filesystem]
            acl:
              allow_sources: [api]
              allow_roles: [admin, system]
            inputs:
              - {name: operation, type: string, required: true}
              - {name: path, type: string, required: true}
          - name: code_exec
            module: code_exec.py
            handler: run
            permissions: [exec]
            acl:
              allow_sources: [api]
              allow_roles: [admin]
            inputs:
              - {name: code, type: string, required: true}
        '''
    )


MODULES = {
    'file_ops.py': 'from app.skills.file_ops import run\n',
    'code_exec.py': 'from app.skills.code_exec import run\n',
}


def test_acl_real_integration_denies_anonymous_file_ops(client, isolated_skill_manager):
    settings.enable_skill_acl = True
    settings.enable_skill_validation = True
    settings.api_key = ''
    settings.admin_token = ''
    isolated_skill_manager(_manifest(), MODULES)

    resp = client.post('/v1/skills/invoke', json={'name': 'file_ops', 'inputs': {'operation': 'exists', 'path': '/tmp'}})
    assert resp.status_code == 400
    body = resp.json()['detail']
    assert body['code'] == 'SKILL_ACCESS_DENIED'
    assert body['details']['name'] == 'file_ops'
    assert 'admin' in body['message'] or 'requires' in body['message']



def test_acl_real_integration_allows_admin_file_ops(client, isolated_skill_manager, monkeypatch, tmp_path):
    settings.enable_skill_acl = True
    settings.enable_skill_validation = True
    settings.api_key = 'user-key'
    settings.admin_token = 'admin-key'
    _, skills_dir = isolated_skill_manager(_manifest(), MODULES)
    monkeypatch.setenv('ARCHILLX_FILE_WHITELIST', str(skills_dir))
    target = skills_dir / 'hello.txt'
    target.write_text('hello', encoding='utf-8')

    resp = client.post(
        '/v1/skills/invoke',
        json={'name': 'file_ops', 'inputs': {'operation': 'read', 'path': str(target)}},
        headers={'x-api-key': 'admin-key'},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['output']['content'] == 'hello'
    assert body['error'] is None



def test_acl_real_integration_denies_api_key_for_code_exec(client, isolated_skill_manager):
    settings.enable_skill_acl = True
    settings.enable_skill_validation = True
    settings.api_key = 'user-key'
    settings.admin_token = 'admin-key'
    isolated_skill_manager(_manifest(), MODULES)

    resp = client.post(
        '/v1/skills/invoke',
        json={'name': 'code_exec', 'inputs': {'code': 'print(1)'}},
        headers={'x-api-key': 'user-key'},
    )
    assert resp.status_code == 400
    body = resp.json()['detail']
    assert body['code'] == 'SKILL_ACCESS_DENIED'
    assert body['details']['name'] == 'code_exec'



def test_acl_real_integration_admin_code_exec_runs_in_process_worker(client, isolated_skill_manager, monkeypatch):
    settings.enable_skill_acl = True
    settings.enable_skill_validation = True
    settings.api_key = 'user-key'
    settings.admin_token = 'admin-key'
    isolated_skill_manager(_manifest(), MODULES)
    monkeypatch.setenv('ARCHILLX_ENABLE_CODE_EXEC', 'true')
    monkeypatch.setenv('ARCHILLX_SANDBOX_BACKEND', 'process')

    resp = client.post(
        '/v1/skills/invoke',
        json={'name': 'code_exec', 'inputs': {'code': 'print(40 + 2)'}},
        headers={'x-api-key': 'admin-key'},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['output']['success'] is True
    assert body['output']['backend'] == 'process'
    assert body['output']['worker_mode'] is True
    assert body['output']['stdout'].strip() == '42'
    assert body['error'] is None



def test_validation_real_integration_missing_required_code_returns_400(client, isolated_skill_manager):
    settings.enable_skill_acl = True
    settings.enable_skill_validation = True
    settings.api_key = 'user-key'
    settings.admin_token = 'admin-key'
    isolated_skill_manager(_manifest(), MODULES)

    resp = client.post(
        '/v1/skills/invoke',
        json={'name': 'code_exec', 'inputs': {}},
        headers={'x-api-key': 'admin-key'},
    )
    assert resp.status_code == 400
    body = resp.json()['detail']
    assert body['code'] == 'SKILL_INPUT_INVALID'
    assert body['details']['name'] == 'code_exec'
