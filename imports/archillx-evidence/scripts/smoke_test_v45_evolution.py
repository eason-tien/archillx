from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.utils.telemetry import telemetry


def main() -> int:
    tmp = ROOT / "evidence" / "_smoke_v45"
    old = settings.evidence_dir
    settings.evidence_dir = str(tmp)
    telemetry.reset()
    telemetry.incr("http_requests_total", 3)
    telemetry.incr("http_status_500_total", 1)
    client = TestClient(app)
    try:
        report = client.post("/v1/evolution/report/run")
        assert report.status_code == 200, report.text
        plan = client.post("/v1/evolution/plan/run")
        assert plan.status_code == 200, plan.text
        assert (tmp / "evolution" / "inspections").exists()
        assert (tmp / "evolution" / "plans").exists()
    finally:
        settings.evidence_dir = old
    print("OK_V45_EVOLUTION_SMOKE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
