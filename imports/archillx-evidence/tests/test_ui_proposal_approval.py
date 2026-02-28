from fastapi.testclient import TestClient

from app.main import app


def test_ui_contains_proposal_action_controls():
    client = TestClient(app)
    r = client.get('/ui')
    assert r.status_code == 200
    text = r.text
    assert 'Approval actions' in text
    assert 'btn-approve' in text
    assert 'btn-reject' in text
    assert 'btn-apply' in text
    assert 'btn-rollback' in text
    assert 'btn-render-artifacts' in text


def test_ui_js_wires_evolution_action_endpoints():
    client = TestClient(app)
    r = client.get('/ui/static/app.js')
    assert r.status_code == 200
    js = r.text
    assert '/v1/evolution/proposals/${selectedProposalId}/${kind}' in js
    assert '/v1/evolution/proposals/${selectedProposalId}/artifacts/render' in js
    assert '/v1/evolution/actions/list?limit=20' in js
    for needle in ['approve', 'reject', 'apply', 'rollback']:
        assert f"runProposalAction('{needle}')" in js
