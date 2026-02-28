"""ArcHillx — Python Code Execution Skill (sandboxed subprocess)"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

_BLOCKED = [
    "os.system", "os.popen", "__import__", "eval(", "exec(",
    "open(", "shutil", "socket", "requests", "urllib",
    "rm -rf", "shutdown", "reboot",
]
_MAX_TIMEOUT_S = 30
_MAX_CODE_LEN = 20000


def _scan(code: str) -> str | None:
    cl = code.lower()
    for blocked in _BLOCKED:
        if blocked.lower() in cl:
            return f"Security violation: '{blocked}' not allowed."
    return None


def _safe_timeout(raw: object) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 10
    if value < 1:
        return 1
    return min(value, _MAX_TIMEOUT_S)


def run(inputs: dict) -> dict:
    code = str(inputs.get("code", ""))
    if not code:
        return {"error": "code required", "stdout": "", "stderr": "", "exit_code": 1}
    if len(code) > _MAX_CODE_LEN:
        return {
            "error": f"code too long ({len(code)} > {_MAX_CODE_LEN})",
            "stdout": "",
            "stderr": "",
            "exit_code": 1,
        }

    timeout = _safe_timeout(inputs.get("timeout_s", 10))
    violation = _scan(code)
    if violation:
        return {"error": violation, "stdout": "", "stderr": violation, "exit_code": 1}

    tmp_path = None
    with tempfile.TemporaryDirectory(prefix="archillx_code_exec_") as workdir:
        try:
            tmp_path = Path(workdir) / "snippet.py"
            tmp_path.write_text(code, encoding="utf-8")
            env = {
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PATH": os.environ.get("PATH", ""),
                "LANG": os.environ.get("LANG", "C.UTF-8"),
            }
            result = subprocess.run(
                [sys.executable, "-I", str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workdir,
                env=env,
            )
            return {
                "stdout": result.stdout[:4096],
                "stderr": result.stderr[:2048],
                "exit_code": result.returncode,
                "error": None if result.returncode == 0 else f"exit {result.returncode}",
            }
        except subprocess.TimeoutExpired:
            return {"error": f"timeout after {timeout}s", "stdout": "", "stderr": "", "exit_code": -1}
        except Exception as e:
            return {"error": str(e), "stdout": "", "stderr": "", "exit_code": -1}
        finally:
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
