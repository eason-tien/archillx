from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.evolution.service import evolution_service


def test_artifact_manifest_endpoint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post('/v1/evolution/report/run')
    client.post('/v1/evolution/plan/run')
    proposal = client.post('/v1/evolution/proposals/generate', json={'item_index': 0}).json()
    pid = proposal['proposal_id']
    client.post(f'/v1/evolution/proposals/{pid}/artifacts/render')
    resp = client.get(f'/v1/evolution/proposals/{pid}/artifacts/manifest')
    assert resp.status_code == 200
    payload = resp.json()['manifest']
    assert payload['proposal_id'] == pid
    assert 'artifact_count' in payload
    assert 'manifest' not in payload
    assert 'patch' in payload['artifact_keys']
