from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from app.main import app
html = (ROOT / 'app/ui/static/index.html').read_text(encoding='utf-8')
assert 'btn-open-gate-portal-preview' in html
assert 'btn-open-restore-preview' in html
client = TestClient(app)
assert client.get('/v1/gates/portal/preview').status_code == 200
assert client.get('/v1/restore-drill/preview').status_code == 200
print('OK_V88_UI_HTML_HUB_SMOKE')
