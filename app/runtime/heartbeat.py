from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from ..config import settings


class HeartbeatWriter:
    def __init__(self):
        self._stop = threading.Event()
        self._thread = None

    def _path(self) -> Path:
        if settings.recovery_heartbeat_path:
            return Path(settings.recovery_heartbeat_path)
        return Path(tempfile.gettempdir()) / "archillx_heartbeat.json"

    def _loop(self):
        p = self._path()
        p.parent.mkdir(parents=True, exist_ok=True)
        while not self._stop.is_set():
            payload = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "epoch": time.time(),
                "pid": os.getpid(),
                "version": settings.app_version,
                "mode": "primary",
            }
            p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            self._stop.wait(timeout=10)

    def startup(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="heartbeat-writer", daemon=True)
        self._thread.start()

    def shutdown(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)


heartbeat_writer = HeartbeatWriter()
