import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests/test_evolution_list_filters.py'], text=True)
if proc.returncode != 0:
    raise SystemExit(proc.returncode)
print('OK_V51_PROPOSAL_LIST_SMOKE')
