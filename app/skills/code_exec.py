"""ArcHillx — Python Code Execution Skill (sandboxed subprocess)"""
from __future__ import annotations

import os, subprocess, sys, tempfile

_BLOCKED = ["os.system", "os.popen", "__import__", "eval(", "exec(",
            "open(", "shutil", "socket", "requests", "urllib",
            "rm -rf", "shutdown", "reboot"]


def _scan(code: str) -> str | None:
    cl = code.lower()
    for b in _BLOCKED:
        if b.lower() in cl:
            return f"Security violation: '{b}' not allowed."
    return None


def run(inputs: dict) -> dict:
    code = inputs.get("code", "")
    if not code:
        return {"error": "code required", "stdout": "", "stderr": "", "exit_code": 1}
    timeout = int(inputs.get("timeout_s", 10))
    v = _scan(code)
    if v:
        return {"error": v, "stdout": "", "stderr": v, "exit_code": 1}
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                         encoding="utf-8") as f:
            f.write(code)
            tmp = f.name
        res = subprocess.run([sys.executable, tmp], capture_output=True,
                             text=True, timeout=timeout,
                             env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        return {"stdout": res.stdout[:4096], "stderr": res.stderr[:2048],
                "exit_code": res.returncode,
                "error": None if res.returncode == 0 else f"exit {res.returncode}"}
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s",
                "stdout": "", "stderr": "", "exit_code": -1}
    except Exception as e:
        return {"error": str(e), "stdout": "", "stderr": "", "exit_code": -1}
    finally:
        if tmp:
            try: os.unlink(tmp)
            except Exception: pass
