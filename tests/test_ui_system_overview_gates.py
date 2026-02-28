from fastapi.testclient import TestClient

from app.main import app


def test_ui_contains_gate_summary_panels():
    client = TestClient(app)
    r = client.get('/ui')
    assert r.status_code == 200
    text = r.text
    assert 'Release / rollback gate summary' in text
    assert 'Gate latest evidence' in text
    assert 'refresh-gates' in text


def test_ui_js_wires_gate_summary_endpoint():
    client = TestClient(app)
    r = client.get('/ui/static/app.js')
    assert r.status_code == 200
    js = r.text
    assert '/v1/gates/summary' in js
    assert 'gates-summary' in js
    assert 'gates-latest' in js
