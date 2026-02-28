from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app


def main():
    client = TestClient(app)
    html = client.get('/ui')
    assert html.status_code == 200
    assert 'Approval actions' in html.text
    js = client.get('/ui/static/app.js')
    assert js.status_code == 200
    for needle in [
        'runProposalAction(\'approve\')',
        'runProposalAction(\'reject\')',
        'runProposalAction(\'apply\')',
        'runProposalAction(\'rollback\')',
        '/artifacts/render',
    ]:
        assert needle in js.text
    print('OK_V71_UI_PROPOSAL_APPROVAL_SMOKE')


if __name__ == '__main__':
    main()
