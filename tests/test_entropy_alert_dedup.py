from __future__ import annotations

from app.config import settings
from app.entropy.engine import EntropyEngine


class _Resp:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


def test_entropy_alert_dedup_within_cooldown(tmp_path, monkeypatch):
    old_evidence = settings.evidence_dir
    old_db = settings.entropy_ops_sqlite_path
    old_url = settings.entropy_alert_webhook_url
    old_cool = settings.entropy_alert_cooldown_s
    settings.evidence_dir = str(tmp_path)
    settings.entropy_ops_sqlite_path = str(tmp_path / 'entropy_ops.sqlite')
    settings.entropy_alert_webhook_url = 'http://example.local/webhook'
    settings.entropy_alert_cooldown_s = 300

    calls = {'n': 0}

    def fake_urlopen(*args, **kwargs):
        calls['n'] += 1
        return _Resp()

    monkeypatch.setattr('app.entropy.engine.urlopen', fake_urlopen)

    try:
        eng = EntropyEngine()
        vec = {'memory': 0.95, 'task': 0.95, 'model': 0.95, 'resource': 0.95, 'decision': 0.95}
        eng.evaluate_from_vector_for_test(vec, persist=True)
        eng.evaluate_from_vector_for_test(vec, persist=True)
        assert calls['n'] == 1
    finally:
        settings.evidence_dir = old_evidence
        settings.entropy_ops_sqlite_path = old_db
        settings.entropy_alert_webhook_url = old_url
        settings.entropy_alert_cooldown_s = old_cool
