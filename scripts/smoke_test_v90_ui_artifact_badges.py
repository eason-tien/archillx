from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app


def main() -> None:
    client = TestClient(app)
    html = client.get('/ui').text
    js = client.get('/ui/static/app.js').text
    assert 'proposal-artifact-badges' in html
    assert 'renderArtifactManifestBadges' in js
    assert 'Artifacts:' in js
    print('OK_V90_UI_ARTIFACT_BADGES_SMOKE')


if __name__ == '__main__':
    main()
