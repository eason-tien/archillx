import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
html = client.get('/ui').text
js = client.get('/ui/static/app.js').text
assert 'Integrated review card' in html
assert 'proposal-guard-summary' in html
assert 'proposal-baseline-summary' in html
assert '/v1/evolution/evidence/nav/proposals/${id}' in js
print('OK_V83_UI_REVIEW_CARDS_SMOKE')
