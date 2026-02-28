from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cmd = [
        sys.executable,
        '-m',
        'pytest',
        'tests/test_api_routes.py',
        'tests/test_api_integration_routes.py',
        'tests/test_api_extension_routes.py',
        'tests/test_api_feature_enabled_routes.py',
        'tests/test_api_audit_routes.py',
        '-q',
    ]
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode
    print('OK_V15_AUDIT_SMOKE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
