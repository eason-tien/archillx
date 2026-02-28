import os, sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
cmd = [sys.executable, '-m', 'pytest', '-q', 'tests/test_ui_evolution_navigation.py']
res = subprocess.run(cmd, text=True)
if res.returncode != 0:
    raise SystemExit(res.returncode)
print('OK_V72_UI_EVOLUTION_NAVIGATION_SMOKE')
