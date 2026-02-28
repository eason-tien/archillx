from __future__ import annotations
from fastapi.testclient import TestClient
from app.main import app
from app.evolution.service import evolution_service

client = TestClient(app)


def _ensure_proposal():
    inspection = evolution_service.run_inspection()
    plan = evolution_service.build_plan(inspection)
    return evolution_service.generate_proposal(plan=plan, item_index=0)


def test_ui_shell_serves_index():
    r = client.get('/ui')
    assert r.status_code == 200
    assert 'ArcHillx Console' in r.text
    js = client.get('/ui/static/app.js')
    assert js.status_code == 200
    assert 'loadOverview' in js.text


def test_proposal_artifacts_render_and_fetch():
    proposal = _ensure_proposal()
    render = client.post(f'/v1/evolution/proposals/{proposal.proposal_id}/artifacts/render')
    assert render.status_code == 200
    payload = render.json()
    assert payload['artifacts']['patch'].endswith('patch.diff')
    fetch = client.get(f'/v1/evolution/proposals/{proposal.proposal_id}/artifacts')
    assert fetch.status_code == 200
    arts = fetch.json()['artifacts']
    assert arts['pr_draft'].endswith('pr_draft.md')
    assert arts['pr_title'].endswith('pr_title.txt')
    assert arts['commit_message'].endswith('commit_message.txt')
    assert arts['risk'].endswith('risk_assessment.json')
