from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app


def main() -> None:
    client = TestClient(app)
    r = client.get('/v1/evolution/final')
    assert r.status_code == 200
    r2 = client.post('/v1/evolution/final/render')
    assert r2.status_code == 200
    data = r2.json()
    for k in ('json','markdown','html'):
        assert Path(data['paths'][k]).exists(), data
    print('OK_V67_EVOLUTION_FINAL_SMOKE')


if __name__ == '__main__':
    main()
