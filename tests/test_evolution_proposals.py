from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.utils.telemetry import telemetry


def test_evolution_proposal_generation(monkeypatch, tmp_path):
    from app.config import settings
    old_evidence = settings.evidence_dir
    settings.evidence_dir = str(tmp_path)
    telemetry.reset()
    telemetry.incr("http_requests_total", 10)
    telemetry.incr("http_status_500_total", 3)
    telemetry.incr("skill_invoke_failure_total", 2)
    client = TestClient(app)
    try:
        r = client.post("/v1/evolution/plan/run")
        assert r.status_code == 200
        plan = r.json()
        assert len(plan["items"]) >= 1

        r2 = client.post("/v1/evolution/proposals/generate", json={"item_index": 0})
        assert r2.status_code == 200
        proposal = r2.json()
        assert proposal["proposal_id"].startswith("prop_")
        assert proposal["plan_id"] == plan["plan_id"]
        assert proposal["risk"]["risk_level"] in ("low", "medium", "high")
        assert len(proposal["suggested_changes"]) >= 1
        assert proposal["evidence_path"].endswith('.json')

        r3 = client.get("/v1/evolution/proposals")
        assert r3.status_code == 200
        latest = r3.json()
        assert latest["proposal_id"] == proposal["proposal_id"]

        rs = client.get("/v1/evolution/status")
        assert rs.status_code == 200
        status = rs.json()
        assert status["proposal"]["proposal_id"] == proposal["proposal_id"]
    finally:
        settings.evidence_dir = old_evidence
