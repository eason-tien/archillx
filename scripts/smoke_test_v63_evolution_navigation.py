from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

r = client.get('/v1/evolution/nav')
assert r.status_code == 200, r.text
j = r.json()
assert '/v1/evolution/nav/render' in j['routes']

r2 = client.post('/v1/evolution/nav/render')
assert r2.status_code == 200, r2.text
j2 = r2.json()
for key in ('json', 'markdown', 'html'):
    p = Path(j2['paths'][key])
    assert p.exists(), f'missing {key}: {p}'

print('OK_V63_EVOLUTION_NAVIGATION_SMOKE')
