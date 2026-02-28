from app.main import app
from fastapi.testclient import TestClient
from app.evolution.service import evolution_service


def _make_action(action_id: str, *, action: str, actor: str, proposal_id: str, from_status: str, to_status: str):
    return {
        "action_id": action_id,
        "created_at": "2026-02-27T00:00:00Z",
        "proposal_id": proposal_id,
        "action": action,
        "actor": actor,
        "reason": None,
        "from_status": from_status,
        "to_status": to_status,
        "evidence_path": f"/tmp/{action_id}.json",
    }


def test_action_list_filters(monkeypatch):
    client = TestClient(app)

    data = [
        _make_action("act1", action="approve", actor="alice", proposal_id="prop1", from_status="guard_passed", to_status="approved"),
        _make_action("act2", action="apply", actor="bob", proposal_id="prop1", from_status="approved", to_status="applied"),
        _make_action("act3", action="reject", actor="alice", proposal_id="prop2", from_status="generated", to_status="rejected"),
    ]

    monkeypatch.setattr("app.evolution.service.list_json", lambda kind, limit=20: data)

    r = client.get("/v1/evolution/actions/list", params={"action": "approve", "actor": "ali", "proposal_id": "prop1"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["action_id"] == "act1"
    assert body["filters"]["action"] == "approve"


def test_action_get_by_id(monkeypatch):
    client = TestClient(app)
    payload = _make_action("act9", action="rollback", actor="ops", proposal_id="prop9", from_status="applied", to_status="rolled_back")
    monkeypatch.setattr(evolution_service, "load_action", lambda action_id: evolution_service.list_actions(limit=1, action=None) or None)
    # overwrite list_actions to return the specific action object model
    from app.evolution.schemas import EvolutionApprovalAction
    monkeypatch.setattr(evolution_service, "load_action", lambda action_id: EvolutionApprovalAction.model_validate(payload) if action_id == "act9" else None)

    r = client.get("/v1/evolution/actions/act9")
    assert r.status_code == 200
    assert r.json()["action"] == "rollback"

    r2 = client.get("/v1/evolution/actions/nope")
    assert r2.status_code == 404
    assert r2.json()["detail"]["code"] == "EVOLUTION_ACTION_NOT_FOUND"
