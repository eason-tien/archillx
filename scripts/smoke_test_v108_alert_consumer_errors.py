from pathlib import Path

base = Path(__file__).resolve().parents[1]
common = (base / "deploy/alertmanager/examples/common_payload.py").read_text()
fastapi_example = (base / "deploy/alertmanager/examples/fastapi_consumer.py").read_text()
flask_example = (base / "deploy/alertmanager/examples/flask_consumer.py").read_text()
doc = (base / "docs/ALERT_WEBHOOK_CONSUMER_TEMPLATE.md").read_text()

assert "PayloadValidationError" in common
assert "INVALID_PAYLOAD" in fastapi_example
assert "INVALID_JSON" in fastapi_example
assert "CONSUMER_ERROR" in fastapi_example
assert "INVALID_PAYLOAD" in flask_example
assert "INVALID_JSON" in flask_example
assert "CONSUMER_ERROR" in flask_example
assert "## Error handling templates" in doc
print("OK_V108_ALERT_CONSUMER_ERRORS_SMOKE")
