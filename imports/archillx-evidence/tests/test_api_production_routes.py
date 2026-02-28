from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.security.audit_store import append_jsonl
from app.utils.telemetry import telemetry


def test_metrics_route_returns_prometheus(client):
    settings.enable_metrics = True
    telemetry.incr('test_counter_total')
    resp = client.get('/v1/metrics')
    assert resp.status_code == 200
    assert 'archillx_test_counter_total' in resp.text
    assert 'archillx_uptime_seconds' in resp.text


def test_telemetry_snapshot_disabled(client):
    settings.enable_telemetry = False
    resp = client.get('/v1/telemetry')
    assert resp.status_code == 503
    assert resp.json()['detail']['code'] == 'TELEMETRY_DISABLED'


def test_telemetry_snapshot_enabled(client):
    settings.enable_telemetry = True
    telemetry.incr('snapshot_counter')
    resp = client.get('/v1/telemetry')
    assert resp.status_code == 200
    body = resp.json()
    assert body['service'] == settings.telemetry_service_name
    assert body['snapshot']['counters']['snapshot_counter'] >= 1


def test_audit_archive_roll_endpoint(client, tmp_path):
    old = settings.evidence_dir
    settings.evidence_dir = str(tmp_path)
    try:
        append_jsonl({'action': 'sandbox_denied', 'decision': 'BLOCKED'})
        resp = client.post('/v1/audit/archive')
        assert resp.status_code == 200
        body = resp.json()
        assert body['rotated'] is True
        assert Path(body['archived_to']).exists()
    finally:
        settings.evidence_dir = old


def test_telemetry_snapshot_aggregate_enabled(client):
    settings.enable_telemetry = True
    telemetry.reset()
    telemetry.incr("http_requests_total", 3)
    telemetry.incr("http_status_200_total", 2)
    telemetry.incr("http_status_500_total", 1)
    telemetry.timing("http_request", 0.2)
    telemetry.timing("http_request", 0.4)
    telemetry.incr("skill_invoke_total", 4)
    telemetry.incr("skill_invoke_success_total", 3)
    telemetry.incr("skill_web_search_invoke_total", 2)
    telemetry.incr("skill_web_search_success_total", 2)
    telemetry.incr("cron_execute_total", 5)
    telemetry.incr("cron_job_nightly_execute_total", 2)
    telemetry.incr("sandbox_events_total", 2)
    telemetry.incr("sandbox_backend_process_total", 2)
    resp = client.get('/v1/telemetry')
    assert resp.status_code == 200
    body = resp.json()
    agg = body['aggregate']
    assert agg['http']['requests_total'] == 3
    assert agg['http']['status']['2xx'] == 2
    assert agg['http']['status']['5xx'] == 1
    assert agg['skills']['totals']['invoke_total'] == 4
    assert agg['skills']['by_skill']['invoke_total']['web_search'] == 2
    assert agg['cron']['by_job']['execute_total']['nightly'] == 2
    assert agg['sandbox']['backend']['process'] == 2


def test_telemetry_history_windows_enabled(client):
    settings.enable_telemetry = True
    telemetry.reset()
    telemetry.incr("http_requests_total", 2)
    telemetry.incr("http_status_200_total", 2)
    telemetry.timing("http_request", 0.1)
    telemetry.incr("skill_invoke_total", 1)
    telemetry.incr("skill_invoke_success_total", 1)
    telemetry.incr("skill_web_search_invoke_total", 1)
    telemetry.incr("skill_web_search_success_total", 1)
    telemetry.incr("cron_execute_total", 1)
    telemetry.incr("cron_success_total", 1)
    telemetry.incr("cron_job_nightly_execute_total", 1)
    telemetry.incr("cron_job_nightly_success_total", 1)
    telemetry.incr("sandbox_events_total", 1)
    telemetry.incr("sandbox_decision_APPROVED_total", 1)
    telemetry.incr("sandbox_backend_process_total", 1)
    resp = client.get('/v1/telemetry')
    assert resp.status_code == 200
    body = resp.json()
    history = body['history']['windows']
    last_60 = history['last_60s']
    assert last_60['http']['requests_total'] == 2
    assert last_60['http']['status']['2xx'] == 2
    assert last_60['http']['latency']['count'] == 1
    assert last_60['skills']['invoke_total'] == 1
    assert last_60['skills']['by_skill']['invoke_total']['web_search'] == 1
    assert last_60['cron']['execute_total'] == 1
    assert last_60['cron']['by_job']['execute_total']['nightly'] == 1
    assert last_60['sandbox']['approved_total'] == 1
    assert last_60['sandbox']['by_backend']['process'] == 1
    assert last_60['sandbox']['by_decision']['APPROVED'] == 1
