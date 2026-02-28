from fastapi.testclient import TestClient

from app.main import app


def test_evolution_evidence_index_api(monkeypatch):
    client = TestClient(app)

    fake_index = {
        "base_dir": "/tmp/evidence/evolution",
        "window_limit": 10,
        "total_items": 3,
        "kinds": {
            "proposals": {
                "count": 1,
                "latest": {"object_id": "prop1"},
                "items": [{"object_id": "prop1", "headline": "tighten sandbox"}],
            },
            "actions": {
                "count": 2,
                "latest": {"object_id": "act2"},
                "items": [{"object_id": "act2"}, {"object_id": "act1"}],
            },
        },
        "navigation": {"latest_proposal": {"proposal_id": "prop1", "last_guard_id": "guard1"}},
    }
    monkeypatch.setattr('app.evolution.service.evidence_index', lambda limit=20: fake_index)

    r = client.get('/v1/evolution/evidence/index', params={'limit': 10})
    assert r.status_code == 200
    body = r.json()
    assert body['window_limit'] == 10
    assert body['kinds']['proposals']['count'] == 1
    assert body['navigation']['latest_proposal']['proposal_id'] == 'prop1'


def test_evolution_evidence_kind_list_api(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        'app.evolution.service.list_evidence',
        lambda kind, limit=20: [{"kind": kind, "object_id": "prop1", "headline": "tighten sandbox"}],
    )

    r = client.get('/v1/evolution/evidence/kinds/proposals', params={'limit': 5})
    assert r.status_code == 200
    body = r.json()
    assert body['kind'] == 'proposals'
    assert body['items'][0]['object_id'] == 'prop1'


def test_evolution_proposal_navigation_api(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        'app.evolution.service.proposal_navigation',
        lambda proposal_id: {
            "proposal": {"proposal_id": proposal_id, "title": "tighten sandbox"},
            "inspection": {"inspection_id": "insp1"},
            "plan": {"plan_id": "plan1"},
            "guard": {"guard_id": "guard1"},
            "baseline": {"baseline_id": "base1"},
            "actions": [{"action_id": "act1"}],
            "dashboards": [],
            "links": {"inspection_id": "insp1", "plan_id": "plan1"},
        },
    )

    r = client.get('/v1/evolution/evidence/nav/proposals/prop1')
    assert r.status_code == 200
    body = r.json()
    assert body['proposal']['proposal_id'] == 'prop1'
    assert body['links']['plan_id'] == 'plan1'


def test_evolution_invalid_evidence_kind(monkeypatch):
    client = TestClient(app)
    def _raise(kind, limit=20):
        raise ValueError('Unsupported evidence kind.')
    monkeypatch.setattr('app.evolution.service.list_evidence', _raise)
    r = client.get('/v1/evolution/evidence/kinds/nope')
    assert r.status_code == 400
    assert r.json()['detail']['code'] == 'EVOLUTION_EVIDENCE_KIND_INVALID'
