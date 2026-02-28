from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.evolution.service import evolution_service


def main():
    client = TestClient(app)
    inspection = evolution_service.run_inspection()
    plan = evolution_service.build_plan(inspection)
    proposal = evolution_service.generate_proposal(plan=plan, item_index=0)
    res = client.post(f"/v1/evolution/proposals/{proposal.proposal_id}/artifacts/render")
    assert res.status_code == 200, res.text
    arts = res.json()["artifacts"]
    assert arts["pr_title"].endswith("pr_title.txt")
    assert arts["commit_message"].endswith("commit_message.txt")
    assert Path(arts["pr_title"]).exists()
    assert Path(arts["commit_message"]).exists()
    print("OK_V73_PATCH_ARTIFACT_SMOKE")


if __name__ == "__main__":
    main()