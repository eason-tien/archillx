from __future__ import annotations

import subprocess
import sys


def main() -> int:
    cmd = [sys.executable, '-m', 'pytest', 'tests', '-q']
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        return proc.returncode
    print('OK_V21_FULL_SMOKE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
