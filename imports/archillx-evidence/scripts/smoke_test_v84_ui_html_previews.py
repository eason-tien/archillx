from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app

html = (ROOT / 'app/ui/static/index.html').read_text(encoding='utf-8')
js = (ROOT / 'app/ui/static/app.js').read_text(encoding='utf-8')
assert 'btn-open-evolution-portal-preview' in html
assert 'btn-open-evolution-final-preview' in html
assert '/v1/evolution/portal/preview' in js
assert '/v1/evolution/final/preview' in js

client = TestClient(app)
for path, token in [('/v1/evolution/portal/preview', 'Evolution Portal'), ('/v1/evolution/final/preview', 'Evolution Final Bundle')]:
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code, r.text)
    assert 'text/html' in r.headers.get('content-type', '')
    assert token in r.text

print('OK_V84_UI_HTML_PREVIEWS_SMOKE')
