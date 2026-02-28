from app.utils.api_errors import bad_request


def test_bad_request_shape():
    err = bad_request("BAD_INPUT", "Invalid input", {"field": "name"})
    assert err.status_code == 400
    assert err.detail["code"] == "BAD_INPUT"
    assert err.detail["message"] == "Invalid input"
    assert err.detail["details"]["field"] == "name"
