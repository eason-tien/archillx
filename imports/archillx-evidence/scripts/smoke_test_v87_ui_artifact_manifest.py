from pathlib import Path
import subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

rc = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests/test_ui_proposal_artifact_preview.py', 'tests/test_evolution_artifact_manifest.py'], cwd=ROOT).returncode
if rc != 0:
    raise SystemExit(rc)
print('OK_V87_UI_ARTIFACT_MANIFEST_SMOKE')
