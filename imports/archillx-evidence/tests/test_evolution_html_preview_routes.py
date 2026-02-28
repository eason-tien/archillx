from fastapi.testclient import TestClient

from app.main import app


def test_evolution_portal_preview_route_returns_html():
    client = TestClient(app)
    r = client.get('/v1/evolution/portal/preview')
    assert r.status_code == 200
    assert 'text/html' in r.headers.get('content-type', '')
    assert 'Evolution Portal' in r.text


def test_evolution_final_preview_route_returns_html():
    client = TestClient(app)
    r = client.get('/v1/evolution/final/preview')
    assert r.status_code == 200
    assert 'text/html' in r.headers.get('content-type', '')
    assert 'Evolution Final Bundle' in r.text
