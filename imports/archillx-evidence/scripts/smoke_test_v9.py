from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.security.audit_store import persist_audit
from app.security.sandbox_policy import validate_docker_backend
from app.skills import code_exec
from app.utils.logging_utils import clear_request_context, set_request_context


def must(cond: bool, msg: str):
    if not cond:
        raise SystemExit(msg)


def main():
    tmp_evidence = ROOT / "evidence"
    tmp_evidence.mkdir(parents=True, exist_ok=True)
    os.environ["EVIDENCE_DIR"] = str(tmp_evidence)
    os.environ["ARCHILLX_ENABLE_CODE_EXEC"] = "true"
    os.environ["ARCHILLX_SANDBOX_BACKEND"] = "process"

    res = code_exec.run({"code": "print(40+2)"})
    must(res.get("success") is True and "42" in (res.get("stdout") or ""), f"process backend failed: {res}")
    must(bool(res.get("run_id")), f"missing run_id: {res}")

    os.environ["ARCHILLX_SANDBOX_BACKEND"] = "docker"
    os.environ["ARCHILLX_SANDBOX_DOCKER_USER"] = "0:0"
    os.environ["ARCHILLX_SANDBOX_REQUIRE_NON_ROOT_USER"] = "true"
    pre = validate_docker_backend()
    must(pre.get("ok") is False, f"expected docker preflight failure: {pre}")

    tokens = set_request_context(request_id="req-v9", session_id="sess-v9", task_id="task-v9")
    try:
        rec = persist_audit(action="sandbox_preflight", decision="BLOCKED", risk_score=90, reason="policy", context={"backend": "docker"})
    finally:
        clear_request_context(tokens)
    evidence = Path(rec["evidence_path"])
    must(evidence.exists(), f"audit evidence not found: {rec}")
    payload = json.loads(evidence.read_text(encoding="utf-8").splitlines()[-1])
    must(payload["context"]["request_context"]["request_id"] == "req-v9", f"request context missing in audit: {payload}")

    print("OK_V9_SMOKE")


if __name__ == "__main__":
    main()
