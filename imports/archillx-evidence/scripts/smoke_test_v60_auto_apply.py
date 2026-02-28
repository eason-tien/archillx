from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

if __name__ == '__main__':
    rc = pytest.main(['-q', 'tests/test_evolution_schedule.py'])
    if rc != 0:
        raise SystemExit(rc)
    print('OK_V60_AUTO_APPLY_SMOKE')
