from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.evolution.service import evolution_service

client = TestClient(app)

resp = client.get('/ui')
assert resp.status_code == 200 and 'ArcHillx Console' in resp.text
proposal = evolution_service.generate_proposal(plan=evolution_service.build_plan(evolution_service.run_inspection()), item_index=0)
resp = client.post(f'/v1/evolution/proposals/{proposal.proposal_id}/artifacts/render')
assert resp.status_code == 200
for key in ('patch','pr_draft','tests','rollout','risk','manifest'):
    assert Path(resp.json()['artifacts'][key]).exists()
print('OK_V70_UI_PATCH_ARTIFACTS_SMOKE')
