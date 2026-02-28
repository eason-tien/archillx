from __future__ import annotations

from pathlib import Path

from app.config import settings


def test_entropy_status_endpoint_shape(client):
    resp = client.get('/v1/entropy/status')
    assert resp.status_code == 200
    body = resp.json()
    assert 'entropy_score' in body
    assert 'entropy_vector' in body
    assert 'risk_level' in body
    assert 'triggered_action' in body
    assert 'predictor' in body


def test_entropy_tick_persists_evidence(client, tmp_path):
    old_dir = settings.evidence_dir
    settings.evidence_dir = str(tmp_path)
    try:
        resp = client.post('/v1/entropy/tick')
        assert resp.status_code == 200
        out = Path(tmp_path) / 'entropy_engine.jsonl'
        assert out.exists()
        content = out.read_text(encoding='utf-8')
        assert 'entropy_score' in content
    finally:
        settings.evidence_dir = old_dir
