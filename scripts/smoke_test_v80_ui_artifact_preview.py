from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
html = client.get('/ui').text
js = client.get('/ui/static/app.js').text
assert 'PR / Commit preview' in html
assert 'Patch / Tests / Rollout preview' in html
assert '/artifacts/preview' in js
print('OK_V80_UI_ARTIFACT_PREVIEW_SMOKE')
