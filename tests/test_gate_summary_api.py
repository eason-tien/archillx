from fastapi.testclient import TestClient

from app.main import app


def test_gate_summary_api_shape():
    client = TestClient(app)
    r = client.get('/v1/gates/summary?limit=5')
    assert r.status_code == 200
    payload = r.json()
    assert payload['service'] == 'ArcHillx'
    assert payload['limit'] == 5
    assert 'summary' in payload
    assert 'release' in payload['summary']
    assert 'rollback' in payload['summary']
