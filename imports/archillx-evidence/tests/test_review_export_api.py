from fastapi.testclient import TestClient
from app.main import app
from app.api import evolution_routes

client = TestClient(app)


def test_review_export_invalid_section(monkeypatch):
    def fake_export(proposal_id, section):
        raise ValueError('Unsupported section')
    monkeypatch.setattr(evolution_routes.evolution_service, 'export_review_section', fake_export)
    r = client.post('/v1/evolution/proposals/p1/review/export?section=nope')
    assert r.status_code == 400
    assert r.json()['detail']['code'] == 'EVOLUTION_REVIEW_EXPORT_INVALID_SECTION'


def test_review_export_ok(monkeypatch):
    monkeypatch.setattr(evolution_routes.evolution_service, 'export_review_section', lambda proposal_id, section: {'proposal_id': proposal_id, 'section': section, 'paths': {'json': 'x.json'}})
    r = client.post('/v1/evolution/proposals/p1/review/export?section=guard')
    assert r.status_code == 200
    body = r.json()
    assert body['proposal_id'] == 'p1'
    assert body['section'] == 'guard'
