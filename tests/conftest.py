from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.utils.rate_limit import rate_limiter


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def restore_settings():
    tracked = {
        'api_key': settings.api_key,
        'app_env': settings.app_env,
        'expose_internal_error_details': settings.expose_internal_error_details,
        'admin_token': settings.admin_token,
        'enable_lmf': settings.enable_lmf,
        'enable_planner': settings.enable_planner,
        'enable_notifications': settings.enable_notifications,
        'enable_proactive': settings.enable_proactive,
        'enable_rate_limit': settings.enable_rate_limit,
        'rate_limit_per_min': settings.rate_limit_per_min,
        'high_risk_rate_limit_per_min': settings.high_risk_rate_limit_per_min,
        'enable_telemetry': settings.enable_telemetry,
        'enable_metrics': settings.enable_metrics,
        'audit_file_max_bytes': settings.audit_file_max_bytes,
        'enable_migration_check': settings.enable_migration_check,
        'require_migration_head': settings.require_migration_head,
        'recovery_heartbeat_path': settings.recovery_heartbeat_path,
        'recovery_heartbeat_ttl_s': settings.recovery_heartbeat_ttl_s,
        'recovery_ready_url': settings.recovery_ready_url,
        'recovery_check_interval_s': settings.recovery_check_interval_s,
        'recovery_lock_backend': settings.recovery_lock_backend,
        'redis_url': settings.redis_url,
    }
    yield settings
    for key, value in tracked.items():
        setattr(settings, key, value)




@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def install_module(monkeypatch) -> Callable[[str, types.ModuleType], types.ModuleType]:
    def _install(name: str, module: types.ModuleType) -> types.ModuleType:
        monkeypatch.setitem(sys.modules, name, module)
        return module
    return _install


@dataclass
class _AuditRow:
    id: int
    action: str
    decision: str
    risk_score: int
    reason: str | None
    created_at: datetime


class _Field:
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return ('eq', self.name, other)

    def __ge__(self, other):
        return ('ge', self.name, other)

    def __le__(self, other):
        return ('le', self.name, other)

    def like(self, pattern: str):
        return ('like', self.name, pattern)


class FakeAuditModel:
    decision = _Field('decision')
    action = _Field('action')
    risk_score = _Field('risk_score')
    created_at = _Field('created_at')


class FakeQuery:
    def __init__(self, rows: list[_AuditRow]):
        self.rows = list(rows)

    def order_by(self, _expr):
        self.rows.sort(key=lambda r: r.created_at, reverse=True)
        return self

    def filter(self, expr):
        op, field, value = expr
        if op == 'eq':
            self.rows = [r for r in self.rows if getattr(r, field) == value]
        elif op == 'ge':
            self.rows = [r for r in self.rows if getattr(r, field) >= value]
        elif op == 'le':
            self.rows = [r for r in self.rows if getattr(r, field) <= value]
        elif op == 'like':
            prefix = value[:-1] if value.endswith('%') else value
            self.rows = [r for r in self.rows if str(getattr(r, field)).startswith(prefix)]
        return self

    def offset(self, n: int):
        self.rows = self.rows[n:]
        return self

    def limit(self, n: int):
        self.rows = self.rows[:n]
        return self

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, rows: list[_AuditRow]):
        self.rows = rows
        self.closed = False

    def query(self, _model):
        return FakeQuery(self.rows)

    def close(self):
        self.closed = True


@pytest.fixture
def fake_audit_db(install_module):
    sessions: list[FakeSession] = []

    def _install(rows: list[_AuditRow]) -> list[FakeSession]:
        def factory():
            s = FakeSession(rows)
            sessions.append(s)
            return s

        fake_schema = types.ModuleType('app.db.schema')
        fake_schema.SessionLocal = factory
        fake_schema.AHAuditLog = FakeAuditModel
        install_module('app.db.schema', fake_schema)

        fake_sqlalchemy = types.ModuleType('sqlalchemy')
        fake_sqlalchemy.desc = lambda x: x
        install_module('sqlalchemy', fake_sqlalchemy)
        return sessions

    return _install


@pytest.fixture
def AuditRow():
    return _AuditRow


@pytest.fixture
def isolated_skill_manager(monkeypatch, tmp_path):
    from app.config import settings
    from app.runtime.skill_manager import skill_manager

    old_local = dict(skill_manager._local)
    old_manifests = dict(skill_manager._manifests)
    old_skills_dir = settings.skills_dir
    old_acl = settings.enable_skill_acl
    old_validation = settings.enable_skill_validation

    def _setup(manifest_yaml: str, modules: dict[str, str]):
        skills_dir = tmp_path / 'skills'
        skills_dir.mkdir(exist_ok=True)
        (skills_dir / '__manifest__.yaml').write_text(manifest_yaml, encoding='utf-8')
        for name, body in modules.items():
            (skills_dir / name).write_text(body, encoding='utf-8')
        skill_manager._local.clear()
        skill_manager._manifests.clear()
        settings.skills_dir = str(skills_dir)
        skill_manager.startup()
        return skill_manager, skills_dir

    yield _setup

    skill_manager._local.clear()
    skill_manager._local.update(old_local)
    skill_manager._manifests.clear()
    skill_manager._manifests.update(old_manifests)
    settings.skills_dir = old_skills_dir
    settings.enable_skill_acl = old_acl
    settings.enable_skill_validation = old_validation
