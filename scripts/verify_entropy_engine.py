from __future__ import annotations

import hashlib
import sys
import json
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.entropy.engine import entropy_engine


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    report: dict = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': {},
    }

    with TestClient(app) as client:
        s = client.get('/v1/entropy/status')
        body = s.json()
        ok_status = s.status_code == 200 and all(k in body for k in ['score', 'vector', 'risk', 'state', 'ts'])
        report['checks']['OK_ENTROPY_STATUS'] = bool(ok_status)
        if ok_status:
            print('OK_ENTROPY_STATUS')

        evidence = Path('evidence/entropy_engine.jsonl')
        before = evidence.read_text(encoding='utf-8').count('\n') if evidence.exists() else 0
        t = client.post('/v1/entropy/tick')
        after = evidence.read_text(encoding='utf-8').count('\n') if evidence.exists() else 0
        ok_tick = t.status_code == 200 and after == before + 1
        report['checks']['OK_ENTROPY_TICK_AUDITED'] = bool(ok_tick)
        if ok_tick:
            print('OK_ENTROPY_TICK_AUDITED')

        # tick min interval behavior: second immediate tick should be skipped
        from app.config import settings as _settings
        old_min = _settings.entropy_tick_min_interval_s
        old_last_tick = entropy_engine._last_tick_ts
        _settings.entropy_tick_min_interval_s = max(1, int(old_min) if int(old_min) > 0 else 5)
        entropy_engine._last_tick_ts = 0.0
        evidence2 = Path('evidence/entropy_engine.jsonl')
        before2 = evidence2.read_text(encoding='utf-8').count('\n') if evidence2.exists() else 0
        first = client.post('/v1/entropy/tick')
        second = client.post('/v1/entropy/tick')
        after2 = evidence2.read_text(encoding='utf-8').count('\n') if evidence2.exists() else 0
        sb = second.json() if second.status_code == 200 else {}
        ok_skip = first.status_code == 200 and second.status_code == 200 and sb.get('skipped') is True and sb.get('reason') == 'tick_min_interval_not_reached' and 'next_allowed_ts' in sb and after2 == before2 + 1
        report['checks']['OK_ENTROPY_TICK_SKIPPED'] = bool(ok_skip)
        if ok_skip:
            print('OK_ENTROPY_TICK_SKIPPED')
        _settings.entropy_tick_min_interval_s = old_min
        entropy_engine._last_tick_ts = old_last_tick

        trend = client.get('/v1/entropy/trend?window=24h&bucket=1h')
        tb = trend.json() if trend.status_code == 200 else {}
        ok_trend = trend.status_code == 200 and 'buckets' in tb and 'transitions' in tb
        report['checks']['OK_ENTROPY_TREND_API'] = bool(ok_trend)
        if ok_trend:
            print('OK_ENTROPY_TREND_API')

        kpi = client.get('/v1/entropy/kpi?window=24h')
        kb = kpi.json() if kpi.status_code == 200 else {}
        ok_kpi = kpi.status_code == 200 and 'avg_score' in kb and 'slo' in kb
        report['checks']['OK_ENTROPY_KPI_API'] = bool(ok_kpi)
        if ok_kpi:
            print('OK_ENTROPY_KPI_API')

        m = client.get('/v1/system/monitor')
        mb = m.json() if m.status_code == 200 else {}
        ok_monitor = m.status_code == 200 and isinstance(mb.get('entropy'), dict) and 'score' in mb['entropy']
        report['checks']['OK_SYSTEM_MONITOR_INCLUDES_ENTROPY'] = bool(ok_monitor)
        if ok_monitor:
            print('OK_SYSTEM_MONITOR_INCLUDES_ENTROPY')

        ui = client.get('/ui')
        ok_ui = ui.status_code == 200 and 'monitor-entropy-json' in ui.text and 'Entropy Engine' in ui.text
        report['checks']['OK_UI_ENTROPY_RENDERED'] = bool(ok_ui)
        if ok_ui:
            print('OK_UI_ENTROPY_RENDERED')

    report['evidence'] = {
        'path': str(evidence),
        'exists': evidence.exists(),
        'sha256': _sha256(evidence) if evidence.exists() else None,
    }

    out = Path('evidence/reports')
    out.mkdir(parents=True, exist_ok=True)
    out_path = out / f"ENTROPY_VERIFY_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'REPORT={out_path}')

    return 0 if all(report['checks'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
