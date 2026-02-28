from __future__ import annotations

import types

from app.config import settings


def test_live_route_returns_alive(client):
    resp = client.get('/v1/live')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'alive'


def test_ready_route_returns_ready_with_all_checks_ok(client, install_module):
    class _DB:
        def execute(self, _stmt):
            stmt = str(_stmt)
            if 'alembic_version' in stmt:
                class _R:
                    def scalar(self):
                        return '20260227_000001'
                return _R()
            return 1
        def close(self):
            return None

    fake_schema = types.ModuleType('app.db.schema')
    fake_schema.SessionLocal = lambda: _DB()
    install_module('app.db.schema', fake_schema)

    fake_sqlalchemy = types.ModuleType('sqlalchemy')
    fake_sqlalchemy.text = lambda x: x
    install_module('sqlalchemy', fake_sqlalchemy)

    fake_skills_mod = types.ModuleType('app.runtime.skill_manager')
    fake_skills_mod.skill_manager = types.SimpleNamespace(list_skills=lambda: [{'name': 'web_search'}])
    install_module('app.runtime.skill_manager', fake_skills_mod)

    fake_cron_mod = types.ModuleType('app.runtime.cron')
    fake_cron_mod.cron_system = types.SimpleNamespace(_started=True)
    install_module('app.runtime.cron', fake_cron_mod)

    resp = client.get('/v1/ready')
    assert resp.status_code == 200
    body = resp.json()
    assert body['status'] == 'ready'
    assert body['checks']['db'] is True
    assert body['checks']['skills'] is True
    assert body['checks']['cron'] is True
    assert body['checks']['audit_dir'] is True
    assert body['checks']['migration'] is True
    assert body['details']['migration']['status'] == 'head'
    assert body['errors'] == []


def test_ready_route_returns_degraded_when_db_check_fails(client, install_module):
    class _DB:
        def execute(self, _stmt):
            raise RuntimeError('db down')
        def close(self):
            return None

    fake_schema = types.ModuleType('app.db.schema')
    fake_schema.SessionLocal = lambda: _DB()
    install_module('app.db.schema', fake_schema)

    fake_sqlalchemy = types.ModuleType('sqlalchemy')
    fake_sqlalchemy.text = lambda x: x
    install_module('sqlalchemy', fake_sqlalchemy)

    fake_skills_mod = types.ModuleType('app.runtime.skill_manager')
    fake_skills_mod.skill_manager = types.SimpleNamespace(list_skills=lambda: [{'name': 'web_search'}])
    install_module('app.runtime.skill_manager', fake_skills_mod)

    fake_cron_mod = types.ModuleType('app.runtime.cron')
    fake_cron_mod.cron_system = types.SimpleNamespace(_started=True)
    install_module('app.runtime.cron', fake_cron_mod)

    resp = client.get('/v1/ready')
    assert resp.status_code == 503
    body = resp.json()
    assert body['status'] == 'degraded'
    assert body['checks']['db'] is False
    assert 'audit_dir' in body['checks']
    assert any('db:' in x for x in body['errors'])


def test_rate_limit_blocks_second_request_when_enabled(client):
    settings.enable_rate_limit = True
    settings.rate_limit_per_min = 1

    first = client.get('/v1/models')
    assert first.status_code == 200
    assert first.headers['x-ratelimit-limit'] == '1'
    assert first.headers['x-ratelimit-remaining'] == '0'

    second = client.get('/v1/models')
    assert second.status_code == 429
    body = second.json()['detail']
    assert body['code'] == 'RATE_LIMITED'
    assert body['bucket'] == 'default'
    assert second.headers['x-ratelimit-limit'] == '1'


def test_high_risk_rate_limit_uses_dedicated_bucket(client):
    settings.enable_rate_limit = True
    settings.high_risk_rate_limit_per_min = 1

    first = client.post('/v1/skills/invoke', json={'name': 'missing_skill', 'inputs': {}})
    assert first.status_code in (400, 404)

    second = client.post('/v1/skills/invoke', json={'name': 'missing_skill', 'inputs': {}})
    assert second.status_code == 429
    assert second.json()['detail']['bucket'] == 'high_risk'



def test_migration_state_route_returns_head_when_current_matches(client, install_module):
    class _DB:
        def execute(self, _stmt):
            class _R:
                def scalar(self):
                    return '20260227_000001'
            return _R()
        def close(self):
            return None

    fake_schema = types.ModuleType('app.db.schema')
    fake_schema.SessionLocal = lambda: _DB()
    install_module('app.db.schema', fake_schema)

    fake_sqlalchemy = types.ModuleType('sqlalchemy')
    fake_sqlalchemy.text = lambda x: x
    install_module('sqlalchemy', fake_sqlalchemy)

    resp = client.get('/v1/migration/state')
    assert resp.status_code == 200
    body = resp.json()
    assert body['status'] == 'head'
    assert body['ok'] is True
    assert body['current'] == '20260227_000001'


def test_migration_state_route_returns_503_when_revision_is_behind(client, install_module):
    class _DB:
        def execute(self, _stmt):
            class _R:
                def scalar(self):
                    return 'old_revision'
            return _R()
        def close(self):
            return None

    fake_schema = types.ModuleType('app.db.schema')
    fake_schema.SessionLocal = lambda: _DB()
    install_module('app.db.schema', fake_schema)

    fake_sqlalchemy = types.ModuleType('sqlalchemy')
    fake_sqlalchemy.text = lambda x: x
    install_module('sqlalchemy', fake_sqlalchemy)

    resp = client.get('/v1/migration/state')
    assert resp.status_code == 503
    body = resp.json()
    assert body['status'] == 'behind'
    assert body['ok'] is False
