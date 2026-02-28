from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cmd = [sys.executable, "-m", "pytest", "-q", "tests/test_evolution_routes.py", "tests/test_evolution_proposals.py"]
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        return proc.returncode
    print("OK_V46_PROPOSAL_SMOKE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
