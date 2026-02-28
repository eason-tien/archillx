from __future__ import annotations

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def _call_error_endpoint(path: str) -> dict:
    with TestClient(app, raise_server_exceptions=False) as local_client:
        resp = local_client.get(path)
    assert resp.status_code == 500
    return resp.json()['detail']


def test_unhandled_error_hides_reason_in_production():
    settings.app_env = 'production'
    settings.expose_internal_error_details = False

    router = APIRouter()

    @router.get('/__test__/raise-hidden')
    async def _raise_hidden():
        raise RuntimeError('sensitive error detail')

    start_count = len(app.router.routes)
    app.include_router(router)
    try:
        detail = _call_error_endpoint('/__test__/raise-hidden')
        assert detail['code'] == 'INTERNAL_SERVER_ERROR'
        assert 'reason' not in detail
    finally:
        del app.router.routes[start_count:]


def test_unhandled_error_exposes_reason_in_development():
    settings.app_env = 'development'
    settings.expose_internal_error_details = False

    router = APIRouter()

    @router.get('/__test__/raise-dev')
    async def _raise_dev():
        raise RuntimeError('dev detail')

    start_count = len(app.router.routes)
    app.include_router(router)
    try:
        detail = _call_error_endpoint('/__test__/raise-dev')
        assert detail['code'] == 'INTERNAL_SERVER_ERROR'
        assert detail['reason'] == 'dev detail'
    finally:
        del app.router.routes[start_count:]


def test_unhandled_error_force_exposes_reason_via_flag():
    settings.app_env = 'production'
    settings.expose_internal_error_details = True

    router = APIRouter()

    @router.get('/__test__/raise-flag')
    async def _raise_flag():
        raise RuntimeError('forced detail')

    start_count = len(app.router.routes)
    app.include_router(router)
    try:
        detail = _call_error_endpoint('/__test__/raise-flag')
        assert detail['code'] == 'INTERNAL_SERVER_ERROR'
        assert detail['reason'] == 'forced detail'
    finally:
        del app.router.routes[start_count:]
