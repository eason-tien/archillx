from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.skills import code_exec


def must(cond: bool, msg: str):
    if not cond:
        raise SystemExit(msg)


def main():
    os.environ["ARCHILLX_ENABLE_CODE_EXEC"] = "true"

    os.environ["ARCHILLX_SANDBOX_BACKEND"] = "process"
    ok = code_exec.run({"code": "import math\nprint(round(math.sqrt(81)))"})
    must(ok.get("success") is True, f"process backend expected success: {ok}")
    must(ok.get("backend") == "process", f"process backend not reported: {ok}")

    os.environ["ARCHILLX_SANDBOX_BACKEND"] = "docker"
    res = code_exec.run({"code": "print(123)"})
    must(res.get("backend") == "docker", f"docker backend not reported: {res}")
    if res.get("success") is True:
        must("123" in (res.get("stdout") or ""), f"docker backend stdout mismatch: {res}")
    else:
        must(any(x in ((res.get("error") or "") + " " + (res.get("stderr") or "")).lower() for x in ["docker", "sandbox"]), f"expected structured docker backend failure: {res}")

    print("OK_V7_SMOKE")


if __name__ == "__main__":
    main()
