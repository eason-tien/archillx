from fastapi.testclient import TestClient

from app.main import app


def test_evolution_dashboard_render(monkeypatch, tmp_path):
    client = TestClient(app)

    monkeypatch.setattr(
        'app.evolution.service.write_dashboard_bundle',
        lambda summary: {'json': str(tmp_path / 'out.json'), 'markdown': str(tmp_path / 'out.md'), 'html': str(tmp_path / 'out.html')},
    )
    monkeypatch.setattr(
        'app.evolution.service.EvolutionService.summary',
        lambda self, limit=50: {
            'window_limit': limit,
            'counts': {'proposals': 2},
            'pipeline': {'pending_approval': 1},
            'proposal_status': {'approved': 1},
            'proposal_risk': {'high': 1},
            'proposal_subjects': {'sandbox': 1},
            'action_types': {'approve': 1},
            'action_actors': {'alice': 1},
            'guard_status': {'passed': 1},
            'baseline_regressions': {'detected': 0, 'clear': 1},
            'latest': {'proposal_id': 'prop1', 'action_id': 'act1'},
            'schedule_overview': {'latest_cycle_id': 'cycle1', 'latest_proposal_count': 2, 'latest_generated_limit': 3},
        },
    )

    r = client.post('/v1/evolution/dashboard/render', params={'limit': 25})
    assert r.status_code == 200
    body = r.json()
    assert body['summary']['window_limit'] == 25
    assert body['summary']['counts']['proposals'] == 2
    assert body['paths']['json'].endswith('out.json')
