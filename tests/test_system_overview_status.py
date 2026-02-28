from fastapi.testclient import TestClient

from app.main import app


def test_system_overview_status_shape():
    client = TestClient(app)
    r = client.get('/v1/system/overview-status')
    assert r.status_code == 200
    payload = r.json()
    assert payload['service'] == 'ArcHillx'
    sections = payload['sections']
    assert 'release' in sections
    assert 'rollback' in sections
    assert 'restore' in sections
    assert 'migration' in sections
    assert 'evolution' in sections
    assert 'last_updated' in sections['release']
    assert 'last_updated' in sections['rollback']
    assert 'last_updated' in sections['restore']
    assert 'last_updated' in sections['evolution']


def test_system_overview_status_includes_timelines(client, monkeypatch):
    from app.api import routes
    monkeypatch.setattr(routes, "_gate_summary", lambda limit: {"release": {"passed": 1, "total": 1, "updated_at": "2026-01-01T00:00:00Z"}, "rollback": {"passed": 0, "total": 1, "updated_at": "2026-01-02T00:00:00Z"}, "latest_paths": ["a.json"]})
    monkeypatch.setattr(routes, "_latest_restore_drill_report", lambda: {"available": True, "latest": "restore_1.json", "updated_at": "2026-01-03T00:00:00Z", "report": {"status": "ok"}})
    monkeypatch.setattr("app.utils.migration_state.get_migration_state", lambda: {"status": "head", "ok": True, "current": "1", "head": "1"})
    resp = client.get("/v1/system/overview-status")
    data = resp.json()
    assert data["sections"]["release"]["timeline"]
    assert data["sections"]["restore"]["timeline"][0]["label"] == "latest report"
