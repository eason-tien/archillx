from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'deploy' / 'alertmanager' / 'examples'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fastapi_consumer as fastapi_consumer
import flask_consumer as flask_consumer
from fastapi.testclient import TestClient


def _payload(domain='platform'):
    return {
        'receiver': f'{domain}-webhook',
        'status': 'firing',
        'groupLabels': {'alertname': 'ArchillxTestAlert'},
        'commonLabels': {'alert_domain': domain, 'severity': 'warning'},
        'commonAnnotations': {'summary': 'Test summary', 'runbook': 'docs/OPERATIONS_RUNBOOK.md'},
        'alerts': [
            {
                'status': 'firing',
                'labels': {'alertname': 'ArchillxTestAlert', 'alert_domain': domain, 'severity': 'warning'},
                'annotations': {'summary': 'Specific summary', 'runbook': 'docs/OPERATIONS_RUNBOOK.md'},
                'startsAt': '2026-02-27T00:00:00Z',
                'fingerprint': 'fp-1',
                'generatorURL': 'http://prometheus/test'
            }
        ],
        'externalURL': 'http://alertmanager'
    }


def test_fastapi_invalid_payload_returns_code():
    client = TestClient(fastapi_consumer.app)
    resp = client.post('/alert', json={'alerts': 'bad'})
    assert resp.status_code == 400
    body = resp.json()
    assert body['detail']['code'] == 'INVALID_PAYLOAD'


def test_fastapi_owner_mapping_integrated():
    client = TestClient(fastapi_consumer.app)
    resp = client.post('/alert', json=_payload('governance'))
    assert resp.status_code == 200
    assert resp.json()['normalized']['owner'] == 'governance-reviewer'


def test_flask_invalid_payload_returns_code():
    client = flask_consumer.app.test_client()
    resp = client.post('/alert', json={'alerts': 'bad'})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body['detail']['code'] == 'INVALID_PAYLOAD'


def test_flask_owner_mapping_integrated():
    client = flask_consumer.app.test_client()
    resp = client.post('/alert', json=_payload('release'))
    assert resp.status_code == 200
    assert resp.get_json()['normalized']['owner'] == 'release-manager'
