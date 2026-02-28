#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    cmd = [sys.executable, '-m', 'pytest', '-q', 'tests/test_evolution_routes.py', 'tests/test_evolution_proposals.py', 'tests/test_evolution_guard.py']
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        return proc.returncode
    print('OK_V47_UPGRADE_GUARD_SMOKE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
