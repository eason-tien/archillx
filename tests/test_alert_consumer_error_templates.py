from pathlib import Path


def test_common_payload_has_validation_error():
    text = Path("deploy/alertmanager/examples/common_payload.py").read_text()
    assert "class PayloadValidationError" in text
    assert "payload.alerts is required" in text


def test_fastapi_template_has_structured_errors():
    text = Path("deploy/alertmanager/examples/fastapi_consumer.py").read_text()
    assert "INVALID_JSON" in text
    assert "INVALID_PAYLOAD" in text
    assert "CONSUMER_ERROR" in text


def test_flask_template_has_structured_errors():
    text = Path("deploy/alertmanager/examples/flask_consumer.py").read_text()
    assert "INVALID_JSON" in text
    assert "INVALID_PAYLOAD" in text
    assert "CONSUMER_ERROR" in text
