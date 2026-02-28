from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

res = client.get('/v1/evolution/portal')
assert res.status_code == 200, res.text
body = res.json()
assert 'blocks' in body
assert '/v1/evolution/evidence/index' in body['blocks']['evidence_entrypoints']

res2 = client.post('/v1/evolution/portal/render')
assert res2.status_code == 200, res2.text
body2 = res2.json()
for key in ('json', 'markdown', 'html'):
    path = Path(body2['paths'][key])
    assert path.exists(), path
print('OK_V64_EVOLUTION_PORTAL_SMOKE')
