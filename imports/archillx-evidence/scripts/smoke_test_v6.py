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

    ok = code_exec.run({"code": "import math\nprint(round(math.sqrt(81)))"})
    must(ok.get("worker_mode") is True, "worker mode should be enabled")
    must(ok.get("success") is True, f"expected success: {ok}")
    must("9" in (ok.get("stdout") or ""), f"expected stdout=9: {ok}")

    bad = code_exec.run({"code": "import os\nprint('x')"})
    must(bad.get("success") is False, "blocked import should fail")
    must("not allowed" in (bad.get("stderr") or "") or "Security violation" in (bad.get("stderr") or ""), f"unexpected stderr: {bad}")

    print("OK_V6_SMOKE")


if __name__ == "__main__":
    main()
