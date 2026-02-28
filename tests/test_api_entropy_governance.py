from __future__ import annotations

from app.config import settings
from app.entropy.engine import entropy_engine


def test_entropy_kpi_and_proposal_flow(tmp_path, client):
    old_evidence = settings.evidence_dir
    old_db = settings.entropy_ops_sqlite_path
    settings.evidence_dir = str(tmp_path)
    settings.entropy_ops_sqlite_path = str(tmp_path / 'entropy_ops.sqlite')
    try:
        entropy_engine.evaluate_from_vector_for_test({'memory': 0.9, 'task': 0.9, 'model': 0.9, 'resource': 0.9, 'decision': 0.9}, persist=True)

        kpi = client.get('/v1/entropy/kpi?window=24h')
        assert kpi.status_code == 200
        kb = kpi.json()
        assert 'avg_score' in kb and 'slo' in kb and 'transitions_count' in kb

        plist = client.get('/v1/entropy/proposals?status=PENDING&limit=10')
        assert plist.status_code == 200
        items = plist.json()['items']
        assert items
        pid = items[0]['proposal_id']

        approve = client.post(f'/v1/entropy/proposals/{pid}/approve', json={'actor': 'tester', 'reason': 'validated'})
        assert approve.status_code == 200
        assert approve.json()['ok'] is True

        execute = client.post(f'/v1/entropy/proposals/{pid}/execute', json={'actor': 'tester'})
        assert execute.status_code == 200
        assert execute.json()['ok'] in {True, False}
    finally:
        settings.evidence_dir = old_evidence
        settings.entropy_ops_sqlite_path = old_db
