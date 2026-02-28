import json
from pathlib import Path

from app.security.audit_store import persist_audit
from app.utils.logging_utils import set_request_context, clear_request_context


def test_persist_audit_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DB_TYPE", "sqlite_memory")
    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path))
    tokens = set_request_context(request_id="req-1", session_id="s-1", task_id="t-1")
    try:
        rec = persist_audit(action="sandbox_denied", decision="BLOCKED", risk_score=95, reason="test", context={"backend": "process"})
    finally:
        clear_request_context(tokens)
    p = Path(rec["evidence_path"])
    assert p.exists()
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    payload = json.loads(lines[-1])
    assert payload["action"] == "sandbox_denied"
    assert payload["context"]["request_context"]["request_id"] == "req-1"
