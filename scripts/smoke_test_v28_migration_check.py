from __future__ import annotations

import subprocess
import sys

cmd = [sys.executable, '-m', 'pytest', 'tests/test_api_system_routes.py', '-q']
res = subprocess.run(cmd, check=True)
print('OK_V28_MIGRATION_CHECK_SMOKE')
