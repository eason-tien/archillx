from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    cmd = [sys.executable, '-m', 'pytest', '-q', 'tests/test_evolution_schedule.py']
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    print('OK_V56_AUTO_APPROVE_SMOKE')
