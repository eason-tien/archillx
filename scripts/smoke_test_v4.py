from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.api_errors import bad_request
from app.utils.logging_utils import clear_request_context, get_request_context, set_request_context


def main():
    tokens = set_request_context(request_id="req-v4", session_id="s-v4", task_id="t-v4")
    try:
        ctx = get_request_context()
        assert ctx["request_id"] == "req-v4"
        assert ctx["session_id"] == "s-v4"
        assert ctx["task_id"] == "t-v4"
    finally:
        clear_request_context(tokens)

    err = bad_request("TEST", "hello", {"ok": True})
    assert err.status_code == 400
    assert err.detail["details"]["ok"] is True
    print("OK_SMOKE_TEST_V4")


if __name__ == "__main__":
    main()
