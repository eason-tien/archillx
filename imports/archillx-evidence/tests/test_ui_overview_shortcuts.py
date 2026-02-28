from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ui_overview_contains_shortcuts():
    res = client.get('/ui')
    html = res.text
    assert res.status_code == 200
    assert 'Migration / restore drill quick status' in html
    assert 'Gate / portal quick links' in html
    assert 'refresh-ops-shortcuts' in html
    assert 'btn-open-gate-portal' in html

def test_restore_and_gate_portal_routes():
    res = client.get('/v1/gates/portal/latest')
    assert res.status_code == 200
    body = res.json()
    assert 'portal' in body
    res2 = client.get('/v1/restore-drill/latest')
    assert res2.status_code in (200,404)
