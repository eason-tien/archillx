from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.security.sandbox_policy import validate_docker_backend
from app.skills import code_exec


def must(cond: bool, msg: str):
    if not cond:
        raise SystemExit(msg)


def main():
    os.environ["ARCHILLX_ENABLE_CODE_EXEC"] = "true"

    os.environ["ARCHILLX_SANDBOX_BACKEND"] = "process"
    ok = code_exec.run({"code": "print(40+2)"})
    must(ok.get("success") is True and "42" in (ok.get("stdout") or ""), f"process backend failed: {ok}")

    os.environ["ARCHILLX_SANDBOX_BACKEND"] = "docker"
    os.environ["ARCHILLX_SANDBOX_REQUIRE_NETWORK_NONE"] = "true"
    os.environ["ARCHILLX_SANDBOX_REQUIRE_NON_ROOT_USER"] = "true"
    os.environ["ARCHILLX_SANDBOX_DOCKER_USER"] = "0:0"
    pre = validate_docker_backend()
    must(pre.get("ok") is False, f"expected docker preflight failure for root user policy: {pre}")
    must(any("non-root" in e.lower() for e in pre.get("errors") or []), f"expected non-root policy error: {pre}")

    res = code_exec.run({"code": "print(123)"})
    must(res.get("backend") == "docker", f"docker backend not reported: {res}")
    must(res.get("success") is False, f"expected docker preflight failure result: {res}")
    must("preflight" in str(res).lower() or res.get("preflight"), f"expected preflight details in result: {res}")

    print("OK_V8_SMOKE")


if __name__ == "__main__":
    main()
