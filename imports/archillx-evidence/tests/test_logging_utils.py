from app.utils.logging_utils import get_request_context, set_request_context, clear_request_context


def test_request_context_roundtrip():
    tokens = set_request_context(request_id="req-1", session_id="s-1", task_id="t-1")
    try:
        ctx = get_request_context()
        assert ctx["request_id"] == "req-1"
        assert ctx["session_id"] == "s-1"
        assert ctx["task_id"] == "t-1"
    finally:
        clear_request_context(tokens)

    ctx = get_request_context()
    assert ctx["request_id"] is None
    assert ctx["session_id"] is None
    assert ctx["task_id"] is None
