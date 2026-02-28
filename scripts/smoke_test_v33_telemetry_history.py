from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.telemetry import telemetry


def main() -> int:
    telemetry.reset()
    telemetry.incr("http_requests_total", 1)
    telemetry.incr("http_status_200_total", 1)
    telemetry.timing("http_request", 0.05)
    telemetry.incr("skill_invoke_total", 1)
    hist = telemetry.history_snapshot()
    windows = hist.get("windows", {})
    assert "last_60s" in windows
    assert windows["last_60s"]["http"]["requests_total"] == 1
    assert windows["last_60s"]["skills"]["invoke_total"] == 1
    print("OK_V33_TELEMETRY_HISTORY_SMOKE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
