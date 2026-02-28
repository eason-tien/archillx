from pathlib import Path
import subprocess, sys

root = Path(__file__).resolve().parents[1]
cp = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests/test_evolution_action_filters.py'], cwd=root, capture_output=True, text=True)
if cp.returncode != 0:
    print(cp.stdout)
    print(cp.stderr)
    raise SystemExit(cp.returncode)
print('OK_V52_ACTION_LIST_SMOKE')
