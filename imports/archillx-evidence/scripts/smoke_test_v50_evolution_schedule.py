
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


def main() -> None:
    old_evidence = settings.evidence_dir
    old_auto = settings.enable_evolution_auto
    settings.evidence_dir = str(ROOT / 'evidence')
    settings.enable_evolution_auto = True
    try:
        client = TestClient(app)
        r = client.post('/v1/evolution/schedule/run', json={'limit': 1})
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload['proposal_count'] >= 1
        s = client.get('/v1/evolution/schedule')
        assert s.status_code == 200, s.text
        assert s.json()['enabled'] is True
        print('OK_V50_EVOLUTION_SCHEDULE_SMOKE')
    finally:
        settings.evidence_dir = old_evidence
        settings.enable_evolution_auto = old_auto


if __name__ == '__main__':
    main()
