# Alert Webhook Consumer Template

This document provides practical consumer templates for Alertmanager webhook payloads.

## Expected fields
- receiver
- status
- groupLabels.alertname
- commonLabels.alert_domain
- commonLabels.severity
- commonAnnotations.summary
- commonAnnotations.runbook
- alerts[]

## Minimal handling flow
1. Parse JSON body
2. Normalize the payload into one or more alert records
3. Map `alert_domain` to an owner
4. Preserve `fingerprint`, `startsAt`, `generatorURL`, `externalURL`
5. Attach the `runbook` link in downstream ticket or chat notifications

## Output shape
Both example consumers normalize the incoming payload into:
- `receiver`
- `status`
- `owner`
- `alert_domain`
- `severity`
- `group_alertname`
- `record_count`
- `records[]`

Each record contains:
- `fingerprint`
- `status`
- `alertname`
- `alert_domain`
- `severity`
- `summary`
- `runbook`
- `startsAt`
- `generatorURL`
- `externalURL`

## FastAPI example
```python
from fastapi import FastAPI, Request
from common_payload import build_alert_records

app = FastAPI(title="Archillx Alert Webhook Consumer")

@app.get('/healthz')
async def healthz() -> dict:
    return {'ok': True}

@app.post('/alert')
async def alert(request: Request) -> dict:
    payload = await request.json()
    normalized = build_alert_records(payload)
    return {'ok': True, 'normalized': normalized}
```

## Flask example
```python
from flask import Flask, request
from common_payload import build_alert_records

app = Flask(__name__)

@app.get('/healthz')
def healthz():
    return {'ok': True}

@app.post('/alert')
def alert():
    payload = request.get_json(force=True)
    normalized = build_alert_records(payload)
    return {'ok': True, 'normalized': normalized}
```

## Shared helper
The examples share a tiny helper:
- `deploy/alertmanager/examples/common_payload.py`

This helper shows one simple pattern for:
- owner mapping
- record normalization
- payload field preservation

## Handoff guidance
Map `alert_domain` to the owner matrix in:
- `docs/ALERTING_RECEIVERS_AND_OWNERS.md`

## Reference files
- `deploy/alertmanager/examples/common_payload.py`
- `deploy/alertmanager/examples/fastapi_consumer.py`
- `deploy/alertmanager/examples/flask_consumer.py`

## Example tests

The bundle now includes two minimal test examples you can adapt in your own repo:

- `deploy/alertmanager/examples/test_fastapi_consumer_example.py`
- `deploy/alertmanager/examples/test_flask_consumer_example.py`

These examples exercise:

- `GET /healthz`
- `POST /alert`
- `build_alert_records(...)` normalization path
- owner mapping resolution


## Error handling templates

The consumer examples now include a minimal error handling pattern for:

- invalid JSON → `INVALID_JSON` + HTTP 400
- invalid payload shape → `INVALID_PAYLOAD` + HTTP 400
- unexpected internal exception → `CONSUMER_ERROR` + HTTP 500

Recommended handling order:
1. parse JSON body
2. validate `alerts[]` structure
3. normalize payload
4. attach owner mapping
5. return normalized records or an explicit structured error

### FastAPI error handling shape
- `detail.code`
- `detail.message`

### Flask error handling shape
- `ok: false`
- `detail.code`
- `detail.message`
