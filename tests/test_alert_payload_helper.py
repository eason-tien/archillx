from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / 'deploy' / 'alertmanager' / 'examples' / 'common_payload.py'
spec = importlib.util.spec_from_file_location('alert_common_payload', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
build_alert_records = module.build_alert_records
OWNER_MAP = module.OWNER_MAP


def test_build_alert_records_maps_owner_from_common_domain() -> None:
    payload = {
        'receiver': 'governance-webhook',
        'status': 'firing',
        'groupLabels': {'alertname': 'ArchillxGovernorBlockedSpike'},
        'commonLabels': {'alert_domain': 'governance', 'severity': 'warning'},
        'commonAnnotations': {'summary': 'Governor blocked spike', 'runbook': 'docs/OPERATIONS_RUNBOOK.md'},
        'externalURL': 'http://alertmanager.local',
        'alerts': [
            {
                'fingerprint': 'abc123',
                'status': 'firing',
                'labels': {'alertname': 'ArchillxGovernorBlockedSpike'},
                'annotations': {},
                'startsAt': '2026-02-27T00:00:00Z',
                'generatorURL': 'http://prometheus/graph?g0.expr=test',
            }
        ],
    }

    out = build_alert_records(payload)
    assert out['owner'] == OWNER_MAP['governance']
    assert out['alert_domain'] == 'governance'
    assert out['severity'] == 'warning'
    assert out['record_count'] == 1
    assert out['records'][0]['summary'] == 'Governor blocked spike'
    assert out['records'][0]['runbook'] == 'docs/OPERATIONS_RUNBOOK.md'


def test_build_alert_records_prefers_per_alert_labels_annotations() -> None:
    payload = {
        'receiver': 'security-webhook',
        'status': 'firing',
        'groupLabels': {'alertname': 'ArchillxSandboxDeniedSpike'},
        'commonLabels': {'alert_domain': 'security', 'severity': 'critical'},
        'commonAnnotations': {'summary': 'Common summary', 'runbook': 'common-runbook.md'},
        'externalURL': 'http://alertmanager.local',
        'alerts': [
            {
                'fingerprint': 'def456',
                'labels': {
                    'alertname': 'ArchillxSandboxDeniedSpike',
                    'alert_domain': 'release',
                    'severity': 'warning',
                },
                'annotations': {
                    'summary': 'Alert-specific summary',
                    'runbook': 'release-runbook.md',
                },
                'startsAt': '2026-02-27T00:00:00Z',
                'generatorURL': 'http://prometheus/graph?g0.expr=test2',
            }
        ],
    }

    out = build_alert_records(payload)
    record = out['records'][0]
    assert record['alert_domain'] == 'release'
    assert record['severity'] == 'warning'
    assert record['summary'] == 'Alert-specific summary'
    assert record['runbook'] == 'release-runbook.md'
    # top-level owner remains based on common alert domain for grouped routing
    assert out['owner'] == OWNER_MAP['security']


def test_build_alert_records_uses_unmapped_owner_for_unknown_domain() -> None:
    payload = {
        'receiver': 'misc-webhook',
        'status': 'resolved',
        'commonLabels': {'alert_domain': 'custom', 'severity': 'info'},
        'alerts': [],
    }

    out = build_alert_records(payload)
    assert out['owner'] == 'unmapped-owner'
    assert out['record_count'] == 0
    assert out['records'] == []
