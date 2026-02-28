from __future__ import annotations

from datetime import datetime, timedelta


def test_audit_summary_returns_aggregates_and_filters(client, fake_audit_db, AuditRow):
    now = datetime(2026, 2, 27, 10, 0, 0)
    rows = [
        AuditRow(1, 'sandbox_execute_done', 'APPROVED', 15, None, now - timedelta(minutes=5)),
        AuditRow(2, 'sandbox_denied', 'BLOCKED', 95, 'policy', now - timedelta(minutes=2)),
        AuditRow(3, 'sandbox_execute_failed', 'WARNED', 72, 'timeout', now),
    ]
    fake_audit_db(rows)

    resp = client.get('/v1/audit/summary')
    assert resp.status_code == 200
    body = resp.json()
    assert body['summary']['total'] == 3
    assert body['summary']['by_decision'] == {'WARNED': 1, 'BLOCKED': 1, 'APPROVED': 1}
    assert body['summary']['by_action']['sandbox_denied'] == 1
    assert body['summary']['risk_buckets'] == {'low': 1, 'medium': 0, 'high': 1, 'critical': 1}
    assert body['summary']['latest_created_at'] == '2026-02-27T10:00:00'
    assert body['filters'] == {
        'decision': None,
        'action': None,
        'action_prefix': None,
        'risk_score_min': None,
        'risk_score_max': None,
        'created_after': None,
        'created_before': None,
    }


def test_audit_summary_supports_filters(client, fake_audit_db, AuditRow):
    now = datetime(2026, 2, 27, 10, 0, 0)
    rows = [
        AuditRow(1, 'sandbox_execute_done', 'APPROVED', 15, None, now - timedelta(hours=2)),
        AuditRow(2, 'sandbox_denied', 'BLOCKED', 95, 'policy', now - timedelta(minutes=30)),
        AuditRow(3, 'skill_denied', 'BLOCKED', 88, 'acl', now - timedelta(minutes=10)),
    ]
    fake_audit_db(rows)

    resp = client.get('/v1/audit/summary?action_prefix=sandbox_&risk_score_min=90&created_after=2026-02-27T09:00:00')
    assert resp.status_code == 200
    body = resp.json()
    assert body['summary']['total'] == 1
    assert body['summary']['by_decision'] == {'BLOCKED': 1}
    assert body['summary']['by_action'] == {'sandbox_denied': 1}
    assert body['summary']['risk_buckets'] == {'low': 0, 'medium': 0, 'high': 0, 'critical': 1}
    assert body['filters']['action_prefix'] == 'sandbox_'
    assert body['filters']['risk_score_min'] == 90
    assert body['filters']['created_after'] == '2026-02-27T09:00:00'


def test_audit_summary_rejects_invalid_ranges(client, fake_audit_db):
    fake_audit_db([])

    resp = client.get('/v1/audit/summary?risk_score_min=90&risk_score_max=10')
    assert resp.status_code == 400
    assert resp.json()['detail']['code'] == 'AUDIT_INVALID_RISK_RANGE'

    resp = client.get('/v1/audit/summary?created_after=2026-02-28T00:00:00&created_before=2026-02-27T00:00:00')
    assert resp.status_code == 400
    assert resp.json()['detail']['code'] == 'AUDIT_INVALID_DATE_RANGE'
