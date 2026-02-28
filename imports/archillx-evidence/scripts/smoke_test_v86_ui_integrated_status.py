
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app

def main():
    client = TestClient(app)
    r = client.get('/v1/system/overview-status')
    assert r.status_code == 200
    body = r.json()
    assert 'sections' in body and 'evolution' in body['sections']
    html = (ROOT / 'app/ui/static/index.html').read_text(encoding='utf-8')
    js = (ROOT / 'app/ui/static/app.js').read_text(encoding='utf-8')
    assert 'Integrated system status' in html
    assert '/v1/system/overview-status' in js
    print('OK_V86_UI_INTEGRATED_STATUS_SMOKE')

if __name__ == '__main__':
    main()
