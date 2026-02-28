from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.utils.telemetry import telemetry


def test_evolution_report_and_plan_flow(monkeypatch, tmp_path):
    from app.config import settings
    old_evidence = settings.evidence_dir
    settings.evidence_dir = str(tmp_path)
    telemetry.reset()
    telemetry.incr("http_requests_total", 10)
    telemetry.incr("http_status_500_total", 2)
    telemetry.incr("skill_invoke_failure_total", 1)
    client = TestClient(app)
    try:
        r = client.post("/v1/evolution/report/run")
        assert r.status_code == 200
        payload = r.json()
        assert payload["inspection_id"].startswith("insp_")
        assert payload["status"] in ("attention", "critical")
        assert payload["evidence_path"].endswith(".json")
        assert any(f["subject"] == "http" for f in payload["findings"])

        r2 = client.post("/v1/evolution/plan/run")
        assert r2.status_code == 200
        plan = r2.json()
        assert plan["plan_id"].startswith("plan_")
        assert plan["inspection_id"] == payload["inspection_id"]
        assert len(plan["items"]) >= 1
        assert any(item["subject"] == "http" for item in plan["items"])

        rs = client.get("/v1/evolution/status")
        assert rs.status_code == 200
        status = rs.json()
        assert status["inspection"]["inspection_id"] == payload["inspection_id"]
        assert status["plan"]["plan_id"] == plan["plan_id"]
    finally:
        settings.evidence_dir = old_evidence
