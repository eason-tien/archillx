from __future__ import annotations

from datetime import datetime


def test_system_monitor_endpoint_shape(client):
    resp = client.get('/v1/system/monitor')
    assert resp.status_code == 200
    body = resp.json()
    assert body['system'] == 'ArcHillx'
    assert 'host' in body
    assert 'ready' in body
    assert 'recovery' in body
    assert 'telemetry' in body
    assert 'entropy' in body
    assert 'timestamp' in body


def test_system_monitor_entropy_consistent_with_status(client):
    s = client.get('/v1/entropy/status')
    m = client.get('/v1/system/monitor')
    assert s.status_code == 200
    assert m.status_code == 200
    s_body = s.json()
    m_body = m.json()['entropy']
    assert s_body['state'] == m_body['state']
    assert abs(float(s_body['score']) - float(m_body['score'])) < 1e-6

    t1 = datetime.fromisoformat(s_body['ts'])
    t2 = datetime.fromisoformat(m_body['ts'])
    assert abs((t2 - t1).total_seconds()) < 2.0
