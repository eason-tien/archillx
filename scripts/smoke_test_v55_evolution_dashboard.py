from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evolution.service import evolution_service

summary = evolution_service.summary(limit=5)
result = evolution_service.render_dashboard_bundle(limit=5)
assert 'summary' in result and 'paths' in result
for key in ('json','markdown','html'):
    path = Path(result['paths'][key])
    assert path.exists(), key
print('OK_V55_EVOLUTION_DASHBOARD_SMOKE')
