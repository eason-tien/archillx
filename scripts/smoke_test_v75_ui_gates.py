from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

r = client.get('/ui')
assert r.status_code == 200
assert 'Release / rollback gate summary' in r.text

js = client.get('/ui/static/app.js')
assert js.status_code == 200
assert '/v1/gates/summary' in js.text

api = client.get('/v1/gates/summary')
assert api.status_code == 200
assert 'summary' in api.json()

print('OK_V75_UI_GATES_SMOKE')
