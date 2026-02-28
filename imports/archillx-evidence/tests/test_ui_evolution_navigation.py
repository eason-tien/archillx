from fastapi.testclient import TestClient

from app.main import app


def test_ui_contains_evolution_navigation_controls():
    client = TestClient(app)
    r = client.get('/ui')
    assert r.status_code == 200
    text = r.text
    assert 'Navigation & portal' in text
    for needle in [
        'btn-open-portal',
        'btn-open-nav',
        'btn-open-final',
        'btn-render-dashboard',
        'btn-render-portal',
        'btn-render-final',
    ]:
        assert needle in text


def test_ui_js_wires_evolution_navigation_endpoints():
    client = TestClient(app)
    r = client.get('/ui/static/app.js')
    assert r.status_code == 200
    js = r.text
    for needle in [
        '/v1/evolution/portal',
        '/v1/evolution/nav',
        '/v1/evolution/final',
        '/v1/evolution/dashboard/render',
        '/v1/evolution/portal/render',
        '/v1/evolution/final/render',
    ]:
        assert needle in js
    assert 'loadEvolutionExtras' in js
    assert 'renderEvolutionBundle' in js
