from __future__ import annotations

from datetime import datetime, timedelta
import json


def test_audit_actions_returns_counts_and_filters(client, fake_audit_db, AuditRow):
    now = datetime(2026, 2, 27, 12, 0, 0)
    rows = [
        AuditRow(1, 'sandbox_denied', 'BLOCKED', 95, 'policy', now),
        AuditRow(2, 'sandbox_execute_done', 'APPROVED', 12, None, now - timedelta(minutes=1)),
        AuditRow(3, 'sandbox_denied', 'BLOCKED', 97, 'policy', now - timedelta(minutes=2)),
        AuditRow(4, 'skill_denied', 'BLOCKED', 88, 'acl', now - timedelta(minutes=3)),
    ]
    fake_audit_db(rows)

    resp = client.get('/v1/audit/actions?decision=blocked&action_prefix=sandbox_')
    assert resp.status_code == 200
    body = resp.json()
    assert body['actions'] == [
        {'action': 'sandbox_denied', 'count': 2},
    ]
    assert body['filters'] == {'decision': 'BLOCKED', 'action_prefix': 'sandbox_'}


def test_audit_decisions_returns_counts(client, fake_audit_db, AuditRow):
    now = datetime(2026, 2, 27, 12, 0, 0)
    rows = [
        AuditRow(1, 'sandbox_denied', 'BLOCKED', 95, 'policy', now),
        AuditRow(2, 'sandbox_denied', 'BLOCKED', 93, 'policy', now - timedelta(minutes=1)),
        AuditRow(3, 'sandbox_denied', 'WARNED', 75, 'slow', now - timedelta(minutes=2)),
    ]
    fake_audit_db(rows)

    resp = client.get('/v1/audit/decisions?action=sandbox_denied')
    assert resp.status_code == 200
    body = resp.json()
    assert body['decisions'] == [
        {'decision': 'BLOCKED', 'count': 2},
        {'decision': 'WARNED', 'count': 1},
    ]
    assert body['filters'] == {'action': 'sandbox_denied'}


def test_audit_export_returns_json_payload(client, fake_audit_db, AuditRow):
    now = datetime(2026, 2, 27, 12, 0, 0)
    rows = [
        AuditRow(1, 'sandbox_denied', 'BLOCKED', 95, 'policy', now),
        AuditRow(2, 'sandbox_execute_done', 'APPROVED', 12, None, now - timedelta(minutes=1)),
    ]
    fake_audit_db(rows)

    resp = client.get('/v1/audit/export?format=json&limit=1')
    assert resp.status_code == 200
    body = resp.json()
    assert body['count'] == 1
    assert body['items'][0]['action'] == 'sandbox_denied'
    assert body['filters']['limit'] == 1
    assert body['filters']['offset'] == 0


def test_audit_export_returns_jsonl_stream(client, fake_audit_db, AuditRow):
    now = datetime(2026, 2, 27, 12, 0, 0)
    rows = [
        AuditRow(1, 'sandbox_denied', 'BLOCKED', 95, 'policy', now),
        AuditRow(2, 'sandbox_execute_done', 'APPROVED', 12, None, now - timedelta(minutes=1)),
    ]
    fake_audit_db(rows)

    resp = client.get('/v1/audit/export?format=jsonl&limit=2')
    assert resp.status_code == 200
    assert resp.headers['content-type'].startswith('application/x-ndjson')
    lines = [json.loads(x) for x in resp.text.strip().splitlines()]
    assert len(lines) == 2
    assert lines[0]['action'] == 'sandbox_denied'
