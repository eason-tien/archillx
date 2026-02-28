import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

res = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests/test_evolution_summary.py'], cwd=ROOT)
if res.returncode != 0:
    raise SystemExit(res.returncode)
print('OK_V53_EVOLUTION_SUMMARY_SMOKE')
