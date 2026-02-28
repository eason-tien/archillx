from __future__ import annotations

import json
import time
from pathlib import Path

from app.config import settings
from app.entropy.engine import entropy_engine


def test_entropy_status_endpoint_shape(client):
    resp = client.get('/v1/entropy/status')
    assert resp.status_code == 200
    body = resp.json()
    for k in ['score', 'vector', 'risk', 'state', 'ts']:
        assert k in body
    assert 'entropy_score' in body
    assert 'entropy_vector' in body


def test_entropy_tick_persists_evidence(client, tmp_path):
    old_dir = settings.evidence_dir
    old_min = settings.entropy_tick_min_interval_s
    old_last_tick = entropy_engine._last_tick_ts
    settings.evidence_dir = str(tmp_path)
    settings.entropy_tick_min_interval_s = 0
    try:
        out = Path(tmp_path) / 'entropy_engine.jsonl'
        before = out.read_text(encoding='utf-8').count('\n') if out.exists() else 0
        resp = client.post('/v1/entropy/tick')
        assert resp.status_code == 200
        assert out.exists()
        after = out.read_text(encoding='utf-8').count('\n')
        assert after == before + 1
        row = json.loads(out.read_text(encoding='utf-8').strip().splitlines()[-1])
        for key in ['timestamp', 'entropy_score', 'entropy_vector', 'risk_level', 'state', 'triggered_action', 'governor_override']:
            assert key in row
    finally:
        settings.evidence_dir = old_dir
        settings.entropy_tick_min_interval_s = old_min
        entropy_engine._last_tick_ts = old_last_tick


def test_entropy_state_machine_transition_audited(tmp_path):
    old_dir = settings.evidence_dir
    old_min = settings.entropy_tick_min_interval_s
    old_last_tick = entropy_engine._last_tick_ts
    settings.evidence_dir = str(tmp_path)
    settings.entropy_tick_min_interval_s = 0
    try:
        vectors = [
            {'memory': 0.05, 'task': 0.05, 'model': 0.05, 'resource': 0.05, 'decision': 0.05},  # NORMAL
            {'memory': 0.40, 'task': 0.40, 'model': 0.40, 'resource': 0.40, 'decision': 0.40},  # WARN
            {'memory': 0.60, 'task': 0.60, 'model': 0.60, 'resource': 0.60, 'decision': 0.60},  # DEGRADED
            {'memory': 0.90, 'task': 0.90, 'model': 0.90, 'resource': 0.90, 'decision': 0.90},  # CRITICAL
            {'memory': 0.10, 'task': 0.10, 'model': 0.10, 'resource': 0.10, 'decision': 0.10},  # RECOVERY
            {'memory': 0.10, 'task': 0.10, 'model': 0.10, 'resource': 0.10, 'decision': 0.10},  # NORMAL
        ]
        states = [entropy_engine.evaluate_from_vector_for_test(v, persist=True)['state'] for v in vectors]
        assert states[:4] == ['NORMAL', 'WARN', 'DEGRADED', 'CRITICAL']
        assert states[4] == 'RECOVERY'
        assert states[5] == 'NORMAL'

        rows = [json.loads(x) for x in (Path(tmp_path) / 'entropy_engine.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
        transitions = [r for r in rows if r.get('event') == 'state_transition']
        assert transitions
        assert any(t.get('from') == 'CRITICAL' and t.get('to') == 'RECOVERY' for t in transitions)
    finally:
        settings.evidence_dir = old_dir
        settings.entropy_tick_min_interval_s = old_min
        entropy_engine._last_tick_ts = old_last_tick


def test_entropy_tick_skip_behavior(client, tmp_path):
    old_dir = settings.evidence_dir
    old_min = settings.entropy_tick_min_interval_s
    old_last_tick = entropy_engine._last_tick_ts
    settings.evidence_dir = str(tmp_path)
    settings.entropy_tick_min_interval_s = 60
    entropy_engine._last_tick_ts = 0.0
    try:
        out = Path(tmp_path) / 'entropy_engine.jsonl'
        before = out.read_text(encoding='utf-8').count('\n') if out.exists() else 0
        r1 = client.post('/v1/entropy/tick')
        r2 = client.post('/v1/entropy/tick')
        assert r1.status_code == 200
        assert r2.status_code == 200
        b2 = r2.json()
        assert b2['skipped'] is True
        assert b2['reason'] == 'tick_min_interval_not_reached'
        assert 'next_allowed_ts' in b2
        after = out.read_text(encoding='utf-8').count('\n') if out.exists() else 0
        assert after == before + 1
    finally:
        settings.evidence_dir = old_dir
        settings.entropy_tick_min_interval_s = old_min
        entropy_engine._last_tick_ts = old_last_tick
