from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import subprocess


def main() -> int:
    cmd = [sys.executable, '-m', 'pytest', '-q', 'tests/test_evolution_routes.py', 'tests/test_evolution_proposals.py', 'tests/test_evolution_guard.py', 'tests/test_evolution_baseline.py']
    proc = subprocess.run(cmd, text=True)
    if proc.returncode != 0:
        return proc.returncode
    print('OK_V48_BASELINE_COMPARE_SMOKE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
