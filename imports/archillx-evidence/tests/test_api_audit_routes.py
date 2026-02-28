from __future__ import annotations

from datetime import datetime, timedelta


def test_audit_route_returns_entries_and_filters_metadata(client, fake_audit_db, AuditRow):
    now = datetime(2026, 2, 27, 10, 0, 0)
    rows = [
        AuditRow(1, 'sandbox_execute_done', 'APPROVED', 15, None, now - timedelta(minutes=5)),
        AuditRow(2, 'sandbox_denied', 'BLOCKED', 95, 'policy', now),
    ]
    fake_audit_db(rows)

    resp = client.get('/v1/audit?limit=1')
    assert resp.status_code == 200
    body = resp.json()
    assert body['filters'] == {'limit': 1, 'offset': 0, 'decision': None, 'action': None, 'action_prefix': None, 'risk_score_min': None, 'risk_score_max': None, 'created_after': None, 'created_before': None}
    assert len(body['entries']) == 1
    assert body['entries'][0]['id'] == 2
    assert body['entries'][0]['decision'] == 'BLOCKED'
    assert body['entries'][0]['created_at'].startswith('2026-02-27T10:00:00')


def test_audit_route_filters_decision_case_insensitive(client, fake_audit_db, AuditRow):
    now = datetime.utcnow()
    rows = [
        AuditRow(1, 'sandbox_execute_done', 'APPROVED', 15, None, now),
        AuditRow(2, 'sandbox_denied', 'BLOCKED', 95, 'policy', now - timedelta(seconds=1)),
    ]
    fake_audit_db(rows)

    resp = client.get('/v1/audit?decision=blocked')
    assert resp.status_code == 200
    body = resp.json()
    assert body['filters']['decision'] == 'BLOCKED'
    assert [e['id'] for e in body['entries']] == [2]


def test_audit_route_filters_action(client, fake_audit_db, AuditRow):
    now = datetime.utcnow()
    rows = [
        AuditRow(1, 'sandbox_execute_done', 'APPROVED', 15, None, now),
        AuditRow(2, 'sandbox_denied', 'BLOCKED', 95, 'policy', now - timedelta(seconds=1)),
        AuditRow(3, 'sandbox_denied', 'WARNED', 70, 'retry', now - timedelta(seconds=2)),
    ]
    fake_audit_db(rows)

    resp = client.get('/v1/audit?action=sandbox_denied')
    assert resp.status_code == 200
    body = resp.json()
    assert body['filters']['action'] == 'sandbox_denied'
    assert [e['id'] for e in body['entries']] == [2, 3]


def test_audit_route_supports_offset_and_risk_filters(client, fake_audit_db, AuditRow):
    now = datetime(2026, 2, 27, 10, 0, 0)
    rows = [
        AuditRow(1, 'sandbox_execute_done', 'APPROVED', 15, None, now - timedelta(minutes=2)),
        AuditRow(2, 'sandbox_denied', 'BLOCKED', 95, 'policy', now - timedelta(minutes=1)),
        AuditRow(3, 'sandbox_execute_failed', 'WARNED', 70, 'retry', now),
    ]
    fake_audit_db(rows)

    resp = client.get('/v1/audit?offset=1&risk_score_min=60&risk_score_max=95')
    assert resp.status_code == 200
    body = resp.json()
    assert body['filters']['offset'] == 1
    assert body['filters']['risk_score_min'] == 60
    assert body['filters']['risk_score_max'] == 95
    assert [e['id'] for e in body['entries']] == [2]


def test_audit_route_supports_action_prefix_and_date_range(client, fake_audit_db, AuditRow):
    now = datetime(2026, 2, 27, 10, 0, 0)
    rows = [
        AuditRow(1, 'sandbox_execute_done', 'APPROVED', 15, None, now - timedelta(hours=2)),
        AuditRow(2, 'sandbox_denied', 'BLOCKED', 95, 'policy', now - timedelta(minutes=30)),
        AuditRow(3, 'skill_denied', 'BLOCKED', 88, 'acl', now - timedelta(minutes=10)),
    ]
    fake_audit_db(rows)

    resp = client.get('/v1/audit?action_prefix=sandbox_&created_after=2026-02-27T09:00:00&created_before=2026-02-27T10:00:00')
    assert resp.status_code == 200
    body = resp.json()
    assert body['filters']['action_prefix'] == 'sandbox_'
    assert body['filters']['created_after'] == '2026-02-27T09:00:00'
    assert body['filters']['created_before'] == '2026-02-27T10:00:00'
    assert [e['id'] for e in body['entries']] == [2]


def test_audit_route_rejects_invalid_risk_range(client, fake_audit_db):
    fake_audit_db([])
    resp = client.get('/v1/audit?risk_score_min=90&risk_score_max=10')
    assert resp.status_code == 400
    body = resp.json()
    assert body['detail']['code'] == 'AUDIT_INVALID_RISK_RANGE'


def test_audit_route_rejects_invalid_date_range(client, fake_audit_db):
    fake_audit_db([])
    resp = client.get('/v1/audit?created_after=2026-02-28T00:00:00&created_before=2026-02-27T00:00:00')
    assert resp.status_code == 400
    body = resp.json()
    assert body['detail']['code'] == 'AUDIT_INVALID_DATE_RANGE'


def test_audit_route_rejects_invalid_limit(client, fake_audit_db):
    fake_audit_db([])
    resp = client.get('/v1/audit?limit=0')
    assert resp.status_code == 422
