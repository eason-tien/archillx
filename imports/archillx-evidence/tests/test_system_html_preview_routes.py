from fastapi.testclient import TestClient
from app.main import app


def test_gate_portal_preview_route_returns_html():
    client = TestClient(app)
    r = client.get('/v1/gates/portal/preview')
    assert r.status_code == 200
    assert 'text/html' in r.headers['content-type']
    assert 'Gate portal preview' in r.text


def test_restore_drill_preview_route_returns_html():
    client = TestClient(app)
    r = client.get('/v1/restore-drill/preview')
    assert r.status_code == 200
    assert 'text/html' in r.headers['content-type']
    assert 'Restore drill preview' in r.text
