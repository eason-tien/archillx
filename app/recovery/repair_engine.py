from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

from .evidence import append_event, write_snapshot


class RepairEngine:
    def __init__(self, offline: bool = False, fence_ok: Callable[[], bool] | None = None):
        self.offline = offline
        self.fence_ok = fence_ok or (lambda: True)

    def _run(self, cmd: list[str], step: str, timeout_s: int = 120) -> bool:
        if not self.fence_ok():
            append_event("repair_abort", step=step, reason="lost_leadership")
            return False
        append_event("repair_step_start", step=step, cmd=" ".join(cmd))
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
            append_event(
                "repair_step_end",
                step=step,
                returncode=res.returncode,
                stdout_tail=(res.stdout or "")[-1000:],
                stderr_tail=(res.stderr or "")[-1000:],
            )
            return res.returncode == 0
        except Exception as e:
            append_event("repair_step_error", step=step, error=str(e))
            return False

    def snapshot(self) -> None:
        append_event("snapshot_start")
        env = {k: ("***" if any(x in k.lower() for x in ["key", "token", "password", "secret"]) else v) for k, v in os.environ.items()}
        write_snapshot("env.json", json.dumps(env, ensure_ascii=False, indent=2))
        py = sys.executable
        self._run([py, "-m", "pip", "freeze"], "pip_freeze")
        self._run([py, "-m", "alembic", "current"], "alembic_current")
        self._run([py, "-m", "alembic", "heads"], "alembic_heads")

    def execute(self) -> dict:
        self.snapshot()
        py = sys.executable
        if not self._run([py, "-m", "pip", "check"], "deps_check"):
            install_cmd = [py, "-m", "pip", "install", "-r", "requirements.txt"]
            if self.offline:
                install_cmd = [
                    py, "-m", "pip", "install", "--no-index", "--find-links", "vendor/wheels", "-r", "requirements.txt"
                ]
            if not self._run(install_cmd, "deps_install", timeout_s=300):
                return {"ok": False, "reason": "deps_install_failed"}

        if not self._run([py, "-m", "alembic", "upgrade", "head"], "migrate", timeout_s=180):
            return {"ok": False, "reason": "migration_failed"}

        start_script = Path("scripts/start_server.sh")
        if start_script.exists():
            if not self._run(["bash", str(start_script)], "restart_primary", timeout_s=120):
                return {"ok": False, "reason": "restart_failed"}

        wait_script = Path("scripts/wait_ready.sh")
        if wait_script.exists():
            if not self._run(["bash", str(wait_script)], "verify_ready", timeout_s=120):
                return {"ok": False, "reason": "ready_failed"}
        else:
            time.sleep(2)

        handoff = Path(tempfile.gettempdir()) / "archillx_handoff.json"
        handoff.write_text(json.dumps({"from": "recovery", "to": "primary", "reason": "ready_restored", "ts": time.time()}), encoding="utf-8")
        append_event("handoff_written", path=str(handoff))
        return {"ok": True}
