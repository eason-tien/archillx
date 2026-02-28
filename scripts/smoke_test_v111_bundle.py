from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


if __name__ == '__main__':
    run(sys.executable, '-m', 'pytest', '-q', 'tests/test_ui_v111_bundle.py', 'tests/test_alert_consumer_integration_examples.py')
    print('OK_V111_BUNDLE_SMOKE')
