from __future__ import annotations

from app.config import settings
from app.entropy.engine import entropy_engine


def test_entropy_trend_endpoint_returns_buckets(tmp_path, client):
    old_evidence = settings.evidence_dir
    old_db = settings.entropy_ops_sqlite_path
    settings.evidence_dir = str(tmp_path)
    settings.entropy_ops_sqlite_path = str(tmp_path / 'entropy_ops.sqlite')
    try:
        entropy_engine.evaluate_from_vector_for_test({'memory': 0.8, 'task': 0.8, 'model': 0.8, 'resource': 0.8, 'decision': 0.8}, persist=True)
        entropy_engine.evaluate_from_vector_for_test({'memory': 0.2, 'task': 0.2, 'model': 0.2, 'resource': 0.2, 'decision': 0.2}, persist=True)

        resp = client.get('/v1/entropy/trend?window=24h&bucket=1h')
        assert resp.status_code == 200
        body = resp.json()
        assert body['window'] == '24h'
        assert body['bucket'] == '1h'
        assert 'buckets' in body
        assert 'transitions' in body
    finally:
        settings.evidence_dir = old_evidence
        settings.entropy_ops_sqlite_path = old_db
