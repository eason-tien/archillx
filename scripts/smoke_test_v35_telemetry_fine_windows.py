from __future__ import annotations

import subprocess
import sys


def main() -> int:
    cmd = [sys.executable, "-m", "pytest", "tests/test_api_production_routes.py", "-q"]
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        return proc.returncode
    print("OK_V35_TELEMETRY_FINE_WINDOWS_SMOKE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
