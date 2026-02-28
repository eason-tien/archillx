from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cmd = [
    sys.executable,
    '-m',
    'pytest',
    'tests/test_api_routes.py',
    'tests/test_api_integration_routes.py',
    '-q',
]
res = subprocess.run(cmd, cwd=ROOT)
if res.returncode != 0:
    raise SystemExit(res.returncode)
print('OK_V11_API_SMOKE')
