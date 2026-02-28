from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.utils.telemetry import telemetry


def test_evolution_baseline_compare_flow(tmp_path):
    from app.config import settings
    old_evidence = settings.evidence_dir
    settings.evidence_dir = str(tmp_path)
    telemetry.reset()
    telemetry.incr("http_requests_total", 10)
    telemetry.incr("http_status_500_total", 1)
    telemetry.incr("skill_invoke_failure_total", 1)
    client = TestClient(app)
    try:
        inspection = client.post("/v1/evolution/report/run").json()
        plan = client.post("/v1/evolution/plan/run").json()
        proposal = client.post("/v1/evolution/proposals/generate", json={"item_index": 0}).json()

        telemetry.incr("http_status_500_total", 2)
        telemetry.incr("skill_invoke_failure_total", 1)

        r = client.post(f"/v1/evolution/proposals/{proposal['proposal_id']}/baseline/run")
        assert r.status_code == 200
        payload = r.json()
        assert payload["proposal_id"] == proposal["proposal_id"]
        assert payload["inspection_id"] == inspection["inspection_id"]
        assert payload["diff"]["http_5xx_total"] >= 2
        assert payload["regression_detected"] is True
        assert payload["evidence_path"].endswith('.json')

        r2 = client.get('/v1/evolution/baseline')
        assert r2.status_code == 200
        latest = r2.json()
        assert latest["baseline_id"] == payload["baseline_id"]

        rs = client.get('/v1/evolution/status')
        assert rs.status_code == 200
        status = rs.json()
        assert status["baseline"]["baseline_id"] == payload["baseline_id"]
    finally:
        settings.evidence_dir = old_evidence
