from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cmd = [sys.executable, '-m', 'pytest', '-q', str(ROOT / 'tests' / 'test_alert_payload_helper.py')]
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode
    print('OK_V104_ALERT_PAYLOAD_HELPER_SMOKE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
