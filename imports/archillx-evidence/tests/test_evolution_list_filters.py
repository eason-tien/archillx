from fastapi.testclient import TestClient

from app.main import app
from app.evolution.service import evolution_service


def _seed():
    inspection = evolution_service.run_inspection()
    plan = evolution_service.build_plan(inspection)
    while len(plan.items) < 3:
        plan.items.append(plan.items[0].model_copy())
        plan.items[-1].title += f" clone{len(plan.items)}"
        plan.items[-1].subject = ["sandbox", "migration", "telemetry"][len(plan.items)-1 if len(plan.items)-1 < 3 else 0]
    p0 = evolution_service.generate_proposal(plan=plan, item_index=0)
    p1 = evolution_service.generate_proposal(plan=plan, item_index=1)
    p2 = evolution_service.generate_proposal(plan=plan, item_index=2)
    # drive some states
    evolution_service.approve_proposal(p0.proposal_id, actor="tester", reason="ok")
    evolution_service.reject_proposal(p1.proposal_id, actor="tester", reason="no")
    return p0, p1, p2


def test_list_proposals_filters():
    client = TestClient(app)
    p0, p1, p2 = _seed()
    r = client.get('/v1/evolution/proposals/list', params={'limit': 10, 'status': 'approved'})
    assert r.status_code == 200
    data = r.json()
    assert data['filters']['status'] == 'approved'
    ids = [x['proposal_id'] for x in data['items']]
    assert p0.proposal_id in ids
    assert all(x['status'] == 'approved' for x in data['items'])

    r = client.get('/v1/evolution/proposals/list', params={'limit': 10, 'risk_level': 'high'})
    assert r.status_code == 200
    assert all(x['risk']['risk_level'] == 'high' for x in r.json()['items'])

    r = client.get('/v1/evolution/proposals/list', params={'limit': 10, 'subject': p0.source_subject})
    assert r.status_code == 200
    items = r.json()['items']
    assert items
    want = p0.source_subject.lower()
    assert all(want in (x['source_subject'] + ' ' + x['title']).lower() for x in items)


def test_get_proposal_by_id_and_not_found():
    client = TestClient(app)
    p0, _, _ = _seed()
    r = client.get(f'/v1/evolution/proposals/{p0.proposal_id}')
    assert r.status_code == 200
    assert r.json()['proposal_id'] == p0.proposal_id

    r = client.get('/v1/evolution/proposals/does_not_exist')
    assert r.status_code == 404
    assert r.json()['detail']['code'] == 'EVOLUTION_PROPOSAL_NOT_FOUND'
