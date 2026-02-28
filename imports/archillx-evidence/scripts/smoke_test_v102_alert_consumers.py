from pathlib import Path

root = Path(__file__).resolve().parents[1]
common = root / 'deploy' / 'alertmanager' / 'examples' / 'common_payload.py'
fastapi = root / 'deploy' / 'alertmanager' / 'examples' / 'fastapi_consumer.py'
flask = root / 'deploy' / 'alertmanager' / 'examples' / 'flask_consumer.py'
doc = root / 'docs' / 'ALERT_WEBHOOK_CONSUMER_TEMPLATE.md'

for p in [common, fastapi, flask, doc]:
    assert p.exists(), f'missing {p}'

common_text = common.read_text()
assert 'OWNER_MAP' in common_text
assert 'build_alert_records' in common_text
assert 'fingerprint' in common_text

fastapi_text = fastapi.read_text()
assert '@app.post("/alert")' in fastapi_text
assert '@app.get("/healthz")' in fastapi_text
assert 'build_alert_records' in fastapi_text

flask_text = flask.read_text()
assert '@app.post("/alert")' in flask_text
assert '@app.get("/healthz")' in flask_text
assert 'build_alert_records' in flask_text

doc_text = doc.read_text()
assert 'Output shape' in doc_text
assert 'common_payload.py' in doc_text
assert 'FastAPI example' in doc_text
assert 'Flask example' in doc_text

print('OK_V102_ALERT_CONSUMERS_SMOKE')
