from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


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
        'tests/test_api_agent_routes.py',
        '-q',
    ]
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        return proc.returncode
    print('OK_V17_AGENT_SMOKE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
