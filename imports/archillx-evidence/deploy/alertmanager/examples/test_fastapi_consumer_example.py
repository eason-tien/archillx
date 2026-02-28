from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # type: ignore
import fastapi_consumer as consumer


def test_healthz() -> None:
    client = TestClient(consumer.app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_alert_normalization() -> None:
    client = TestClient(consumer.app)
    payload = {
        "receiver": "platform-webhook",
        "status": "firing",
        "groupLabels": {"alertname": "ArchillxApi5xxHigh"},
        "commonLabels": {"alert_domain": "platform", "severity": "warning"},
        "commonAnnotations": {
            "summary": "API 5xx rate elevated",
            "runbook": "docs/OPERATIONS_RUNBOOK.md",
        },
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "ArchillxApi5xxHigh",
                    "alert_domain": "platform",
                    "severity": "warning",
                },
                "annotations": {
                    "summary": "API 5xx rate elevated",
                    "runbook": "docs/OPERATIONS_RUNBOOK.md",
                },
                "startsAt": "2026-02-27T12:00:00Z",
                "fingerprint": "abc123",
                "generatorURL": "http://prometheus/graph?g0.expr=...",
            }
        ],
        "externalURL": "http://alertmanager",
    }
    resp = client.post("/alert", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["normalized"]["owner"] == "platform-oncall"
    assert body["normalized"]["record_count"] == 1
    assert body["normalized"]["records"][0]["alertname"] == "ArchillxApi5xxHigh"
