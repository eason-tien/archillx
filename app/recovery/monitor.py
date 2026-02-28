from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from ..config import settings


def _heartbeat_path() -> Path:
    if settings.recovery_heartbeat_path:
        return Path(settings.recovery_heartbeat_path)
    return Path(tempfile.gettempdir()) / "archillx_heartbeat.json"


def check_heartbeat_stale() -> tuple[bool, dict]:
    p = _heartbeat_path()
    if not p.exists():
        return True, {"reason": "missing"}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        ts = float(data.get("epoch", 0))
        age = max(0.0, time.time() - ts)
        ttl = max(5, int(settings.recovery_heartbeat_ttl_s))
        return age > ttl, {"age_s": age, "ttl_s": ttl, "pid": data.get("pid")}
    except Exception as e:
        return True, {"reason": str(e)}


def check_ready() -> tuple[bool, dict]:
    url = settings.recovery_ready_url
    try:
        with urlopen(url, timeout=2) as resp:
            code = int(getattr(resp, "status", 200))
            return code >= 500, {"status_code": code}
    except Exception as e:
        return True, {"error": str(e)}
