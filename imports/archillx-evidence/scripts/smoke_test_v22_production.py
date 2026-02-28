from __future__ import annotations

import subprocess
import sys

cmd = [
    sys.executable,
    '-m',
    'pytest',
    'tests',
    '-q',
]
result = subprocess.run(cmd, check=False)
if result.returncode != 0:
    raise SystemExit(result.returncode)
print('OK_V22_PRODUCTION_SMOKE')
