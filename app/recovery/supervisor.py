from __future__ import annotations

import socket
import tempfile
import time
from pathlib import Path

from ..config import settings
from .evidence import append_event
from .monitor import check_heartbeat_stale, check_ready
from .repair_engine import RepairEngine
from .takeover_lock import RedisLockProvider, build_lock_provider


class RecoverySupervisor:
    def __init__(self, force_takeover: bool = False, offline: bool = False, once: bool = False):
        self.force_takeover = force_takeover
        self.offline = offline
        self.once = once
        self.owner = f"{socket.gethostname()}:{int(time.time())}"
        self.provider = build_lock_provider()
        self.handle = None

    def _need_takeover(self) -> tuple[bool, dict]:
        ready_fail, ready_detail = check_ready()
        hb_stale, hb_detail = check_heartbeat_stale()
        score = int(bool(ready_fail)) + int(bool(hb_stale))
        need = self.force_takeover or score >= 2
        return need, {"ready_fail": ready_fail, "ready": ready_detail, "heartbeat_stale": hb_stale, "heartbeat": hb_detail, "score": score}

    def _fence_ok(self) -> bool:
        if isinstance(self.provider, RedisLockProvider) and self.handle is not None:
            return self.provider.is_leader(self.handle.token)
        return True

    def run(self) -> int:
        append_event("recovery_supervisor_start", owner=self.owner)
        interval = max(1, int(settings.recovery_check_interval_s))
        while True:
            need, detail = self._need_takeover()
            append_event("recovery_check", **detail)
            if need:
                append_event("takeover_attempt", owner=self.owner)
                if isinstance(self.provider, RedisLockProvider):
                    self.handle = self.provider.acquire(self.owner, settings.recovery_lock_ttl_s)
                else:
                    self.handle = self.provider.acquire(self.owner)
                if not self.handle:
                    append_event("takeover_lock_busy", owner=self.owner)
                else:
                    append_event("takeover_acquired", owner=self.owner, token=self.handle.token)
                    state = Path(tempfile.gettempdir()) / "archillx_recovery_state.json"
                    state.write_text('{"mode":"recovery"}', encoding="utf-8")
                    engine = RepairEngine(offline=self.offline, fence_ok=self._fence_ok)
                    result = engine.execute()
                    append_event("recovery_result", **result)
                    if isinstance(self.provider, RedisLockProvider):
                        self.provider.release(self.owner)
                    else:
                        self.provider.release()
                    if result.get("ok"):
                        return 0
                    if self.once:
                        return 2
            if self.once:
                return 1
            time.sleep(interval)
