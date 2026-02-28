from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.evolution.upgrade_guard import UpgradeGuard


def test_evolution_approval_state_flow(monkeypatch, tmp_path):
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
        client.post('/v1/evolution/plan/run')
        proposal = client.post('/v1/evolution/proposals/generate', json={'item_index': 0}).json()

        # applying before approval should fail for human-reviewed proposals
        bad_apply = client.post(f"/v1/evolution/proposals/{proposal['proposal_id']}/apply", json={'actor': 'alice'})
        assert bad_apply.status_code == 400
        assert bad_apply.json()['detail']['code'] == 'EVOLUTION_INVALID_TRANSITION'

        guard = client.post(f"/v1/evolution/proposals/{proposal['proposal_id']}/guard/run", json={'mode': 'quick'}).json()
        assert guard['status'] == 'passed'

        approved = client.post(
            f"/v1/evolution/proposals/{proposal['proposal_id']}/approve",
            json={'actor': 'alice', 'reason': 'reviewed'}
        )
        assert approved.status_code == 200
        payload = approved.json()
        assert payload['proposal']['status'] == 'approved'
        assert payload['proposal']['approved_by'] == 'alice'
        assert payload['action']['action'] == 'approve'
        assert payload['action']['from_status'] == 'guard_passed'
        assert payload['action']['to_status'] == 'approved'

        applied = client.post(
            f"/v1/evolution/proposals/{proposal['proposal_id']}/apply",
            json={'actor': 'deployer', 'reason': 'rollout start'}
        )
        assert applied.status_code == 200
        payload2 = applied.json()
        assert payload2['proposal']['status'] == 'applied'
        assert payload2['proposal']['applied_by'] == 'deployer'
        assert payload2['action']['action'] == 'apply'
        assert payload2['action']['from_status'] == 'approved'
        assert payload2['action']['to_status'] == 'applied'

        rolled = client.post(
            f"/v1/evolution/proposals/{proposal['proposal_id']}/rollback",
            json={'actor': 'operator', 'reason': 'post-check failed'}
        )
        assert rolled.status_code == 200
        payload3 = rolled.json()
        assert payload3['proposal']['status'] == 'rolled_back'
        assert payload3['proposal']['rolled_back_by'] == 'operator'
        assert payload3['action']['action'] == 'rollback'
        assert payload3['action']['from_status'] == 'applied'
        assert payload3['action']['to_status'] == 'rolled_back'

        actions = client.get('/v1/evolution/actions').json()
        assert len(actions) >= 3
        assert actions[0]['action'] in {'rollback', 'apply', 'approve'}

        status = client.get('/v1/evolution/status').json()
        assert status['proposal']['status'] == 'rolled_back'
        assert status['action']['action'] == 'rollback'
    finally:
        settings.evidence_dir = old_evidence
