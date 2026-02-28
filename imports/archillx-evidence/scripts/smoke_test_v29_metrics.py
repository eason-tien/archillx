from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
res = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_telemetry_metrics_detail.py', '-q'], cwd=str(ROOT))
if res.returncode != 0:
    raise SystemExit(res.returncode)
print('OK_V29_METRICS_SMOKE')
