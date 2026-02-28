from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from app.config import settings
from app.recovery.monitor import check_heartbeat_stale


def test_heartbeat_stale_when_missing():
    settings.recovery_heartbeat_path = str(Path(tempfile.gettempdir()) / 'not-exists-heartbeat.json')
    stale, detail = check_heartbeat_stale()
    assert stale is True
    assert detail['reason'] == 'missing'


def test_heartbeat_not_stale_when_fresh(tmp_path):
    hb = tmp_path / 'hb.json'
    hb.write_text(json.dumps({'epoch': time.time(), 'pid': 1}), encoding='utf-8')
    settings.recovery_heartbeat_path = str(hb)
    settings.recovery_heartbeat_ttl_s = 90
    stale, detail = check_heartbeat_stale()
    assert stale is False
    assert detail['ttl_s'] == 90
