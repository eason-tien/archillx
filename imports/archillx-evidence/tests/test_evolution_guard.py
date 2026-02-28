from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.evolution.upgrade_guard import UpgradeGuard


def test_evolution_guard_flow(monkeypatch, tmp_path):
    from app.config import settings
    old_evidence = settings.evidence_dir
    settings.evidence_dir = str(tmp_path)

    def fake_run_cmd(self, cmd, timeout=900):
        class R:
            ok = True
            output = 'ok'
        return R()

    monkeypatch.setattr(UpgradeGuard, '_run_cmd', fake_run_cmd, raising=True)

    client = TestClient(app)
    try:
        plan = client.post('/v1/evolution/plan/run').json()
        proposal = client.post('/v1/evolution/proposals/generate', json={'item_index': 0}).json()
        r = client.post(f"/v1/evolution/proposals/{proposal['proposal_id']}/guard/run", json={'mode': 'quick'})
        assert r.status_code == 200
        payload = r.json()
        assert payload['proposal_id'] == proposal['proposal_id']
        assert payload['status'] == 'passed'
        assert len(payload['checks']) >= 6
        assert payload['evidence_path'].endswith('.json')

        r2 = client.get('/v1/evolution/guard')
        assert r2.status_code == 200
        latest = r2.json()
        assert latest['guard_id'] == payload['guard_id']

        rs = client.get('/v1/evolution/status')
        assert rs.status_code == 200
        status = rs.json()
        assert status['guard']['guard_id'] == payload['guard_id']
    finally:
        settings.evidence_dir = old_evidence
