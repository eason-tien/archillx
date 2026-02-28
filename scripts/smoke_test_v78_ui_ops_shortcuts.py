import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
html = client.get('/ui').text
assert 'Migration / restore drill quick status' in html
assert 'Gate / portal quick links' in html
assert client.get('/v1/gates/portal/latest').status_code == 200
assert client.get('/v1/migration/state').status_code in (200,503)
assert client.get('/v1/restore-drill/latest').status_code in (200,404)
print('OK_V78_UI_OPS_SHORTCUTS_SMOKE')
