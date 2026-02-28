from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flask_consumer as consumer


def test_healthz() -> None:
    client = consumer.app.test_client()
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_alert_normalization() -> None:
    client = consumer.app.test_client()
    payload = {
        "receiver": "security-webhook",
        "status": "firing",
        "groupLabels": {"alertname": "ArchillxSandboxDeniedSpike"},
        "commonLabels": {"alert_domain": "security", "severity": "critical"},
        "commonAnnotations": {
            "summary": "Sandbox denied rate elevated",
            "runbook": "docs/ALERTING.md",
        },
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "ArchillxSandboxDeniedSpike",
                    "alert_domain": "security",
                    "severity": "critical",
                },
                "annotations": {
                    "summary": "Sandbox denied rate elevated",
                    "runbook": "docs/ALERTING.md",
                },
                "startsAt": "2026-02-27T12:05:00Z",
                "fingerprint": "xyz789",
                "generatorURL": "http://prometheus/graph?g0.expr=...",
            }
        ],
        "externalURL": "http://alertmanager",
    }
    resp = client.post("/alert", json=payload)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["normalized"]["owner"] == "security-oncall"
    assert body["normalized"]["record_count"] == 1
    assert body["normalized"]["records"][0]["alert_domain"] == "security"
