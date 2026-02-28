from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cmd = [sys.executable, '-m', 'pytest', 'tests/test_api_routes.py', '-q']
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        print('FAIL_V10_API_SMOKE')
        return proc.returncode
    print('OK_V10_API_SMOKE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
