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
    'tests/test_api_extension_routes.py',
    'tests/test_api_feature_enabled_routes.py',
    'tests/test_api_audit_routes.py',
    'tests/test_api_audit_summary_routes.py',
    'tests/test_api_agent_routes.py',
    'tests/test_api_security_routes.py',
    'tests/test_api_security_integration.py',
    'tests/test_main_loop_integration.py',
    '-q',
]
res = subprocess.run(cmd, cwd=str(ROOT))
if res.returncode != 0:
    raise SystemExit(res.returncode)
print('OK_V20_SECURITY_INTEGRATION_SMOKE')
