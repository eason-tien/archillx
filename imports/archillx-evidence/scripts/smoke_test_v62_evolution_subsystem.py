
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evolution.service import evolution_service

payload = evolution_service.render_subsystem_bundle(limit=20)
paths = payload['paths']
for key in ('json', 'markdown', 'html'):
    path = Path(paths[key])
    assert path.exists(), f'missing {key} bundle: {path}'
print('OK_V62_EVOLUTION_SUBSYSTEM_SMOKE')
