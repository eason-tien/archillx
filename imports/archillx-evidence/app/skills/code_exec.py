"""ArcHillx — Python Code Execution Skill (worker-isolated execution)"""
from __future__ import annotations

import ast
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from app.security.audit_store import persist_audit
from app.security.sandbox_policy import (
    docker_apparmor_profile,
    docker_image,
    docker_network_mode,
    docker_seccomp_profile,
    docker_user,
    require_cap_drop_all,
    require_network_none,
    require_no_new_privileges,
    require_read_only_rootfs,
    sandbox_backend,
    validate_docker_backend,
)
from app.utils.logging_utils import structured_log
from app.utils.telemetry import telemetry

logger = logging.getLogger(__name__)

_ALLOWED_IMPORTS = {
    "math", "statistics", "random", "re", "json", "datetime",
    "itertools", "functools", "collections", "string", "fractions", "decimal",
}
_BLOCKED_NAMES = {
    "eval", "exec", "compile", "open", "input", "help", "breakpoint",
    "globals", "locals", "vars", "dir", "getattr", "setattr", "delattr",
    "__import__", "exit", "quit",
}
_BLOCKED_MODULE_PREFIXES = ("os", "sys", "subprocess", "socket", "pathlib", "shutil", "resource", "signal", "ctypes", "multiprocessing", "threading", "asyncio", "importlib", "urllib", "requests")


def _is_enabled() -> bool:
    return os.getenv("ARCHILLX_ENABLE_CODE_EXEC", "false").strip().lower() in {"1", "true", "yes", "on"}


def _sandbox_backend() -> str:
    return sandbox_backend()


def _docker_image() -> str:
    return docker_image()


def _docker_network_mode() -> str:
    return docker_network_mode()


def _docker_memory_limit() -> str:
    return os.getenv("ARCHILLX_SANDBOX_DOCKER_MEMORY", "128m").strip() or "128m"


def _docker_cpus() -> str:
    return os.getenv("ARCHILLX_SANDBOX_DOCKER_CPUS", "0.50").strip() or "0.50"


def _docker_pids_limit() -> str:
    return os.getenv("ARCHILLX_SANDBOX_DOCKER_PIDS", "64").strip() or "64"


def _docker_user() -> str:
    return docker_user()


def _docker_seccomp_profile() -> str:
    return docker_seccomp_profile()


def _docker_apparmor_profile() -> str:
    return docker_apparmor_profile()


def _max_code_bytes() -> int:
    return max(256, int(os.getenv("ARCHILLX_CODE_MAX_BYTES", "12000")))


def _max_stdout_bytes() -> int:
    return max(256, min(int(os.getenv("ARCHILLX_CODE_MAX_STDOUT_BYTES", "4096")), 32768))


def _max_stderr_bytes() -> int:
    return max(256, min(int(os.getenv("ARCHILLX_CODE_MAX_STDERR_BYTES", "2048")), 32768))


def _worker_script() -> str:
    return str((Path(__file__).resolve().parent.parent / "security" / "sandbox_worker.py").resolve())


def _worker_dir() -> Path:
    return (Path(__file__).resolve().parent.parent / "security").resolve()


def _build_env(home_dir: str) -> dict:
    return {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": "",
        "PATH": "",
        "HOME": home_dir,
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
    }


def _scan(code: str) -> str | None:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        return f"Syntax error: {e}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.split(".")[0]
                if name not in _ALLOWED_IMPORTS:
                    return f"Import of '{alias.name}' is not allowed."
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if module not in _ALLOWED_IMPORTS:
                return f"Import from '{node.module}' is not allowed."
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_NAMES:
                return f"Security violation: call to '{node.func.id}' not allowed."
            if isinstance(node.func, ast.Attribute) and node.func.attr.startswith("__"):
                return "Security violation: dunder attribute access not allowed."
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                return "Security violation: dunder attribute access not allowed."
        elif isinstance(node, ast.Name):
            if node.id in _BLOCKED_NAMES:
                return f"Security violation: name '{node.id}' not allowed."
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            low = node.value.lower()
            if any(prefix in low for prefix in _BLOCKED_MODULE_PREFIXES):
                return "Security violation: blocked module reference detected."
    low = code.lower()
    if any(prefix in low for prefix in _BLOCKED_MODULE_PREFIXES):
        return "Security violation: blocked module reference detected."
    return None


def _preexec():
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
        mem = 128 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        out = 2 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (out, out))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except Exception:
        pass


def _prepare_request(run_dir: Path, code: str) -> tuple[Path, Path]:
    req = run_dir / "request.json"
    resp = run_dir / "response.json"
    req.write_text(json.dumps({
        "code": code,
        "max_stdout": _max_stdout_bytes(),
        "max_stderr": _max_stderr_bytes(),
    }, ensure_ascii=False), encoding="utf-8")
    return req, resp


def _decision_for_event(event: str, fields: dict) -> str:
    if event == "sandbox_denied":
        return "BLOCKED"
    if event == "sandbox_preflight" and not fields.get("ok", False):
        return "BLOCKED"
    if event.endswith("failed"):
        return "WARNED"
    return "APPROVED"


def _risk_for_event(event: str, fields: dict) -> int:
    if event == "sandbox_denied":
        return 95
    if event == "sandbox_preflight" and not fields.get("ok", False):
        return 90
    if event.endswith("failed"):
        return 70
    return 15


def _audit(event: str, **fields):
    structured_log(logger, logging.INFO, event, skill="code_exec", **fields)
    telemetry.incr("sandbox_events_total")
    telemetry.incr(f"sandbox_{event}_total")
    backend = str(fields.get("backend") or "unknown").replace("-", "_")
    telemetry.incr(f"sandbox_backend_{backend}_total")
    decision = _decision_for_event(event, fields)
    telemetry.incr(f"sandbox_decision_{decision.lower()}_total")
    reason = fields.get("reason") or fields.get("error") or fields.get("violation")
    persist_audit(action=event, decision=decision, risk_score=_risk_for_event(event, fields), reason=str(reason) if reason else None, context={"skill": "code_exec", **fields})


def _invoke_process_worker(code: str, timeout: int, run_id: str) -> dict:
    base_dir = tempfile.mkdtemp(prefix="archillx_code_exec_")
    _audit("sandbox_execute_start", backend="process", timeout_s=timeout, run_id=run_id)
    try:
        run_dir = Path(base_dir)
        req, resp = _prepare_request(run_dir, code)
        kwargs = dict(
            args=[sys.executable, "-I", "-S", "-B", _worker_script(), str(req), str(resp)],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_build_env(base_dir),
            cwd=base_dir,
            stdin=subprocess.DEVNULL,
        )
        if os.name != "nt":
            kwargs["preexec_fn"] = _preexec
        res = subprocess.run(**kwargs)
        if res.returncode != 0:
            stderr = (res.stderr or "")[:_max_stderr_bytes()]
            out = {
                "success": False,
                "error": f"sandbox worker exit {res.returncode}",
                "stdout": "",
                "stderr": stderr,
                "exit_code": res.returncode,
                "worker_mode": True,
                "backend": "process",
                "run_id": run_id,
            }
            _audit("sandbox_execute_failed", backend="process", exit_code=res.returncode, stderr=stderr[:200], run_id=run_id)
            return out
        if not resp.exists():
            out = {
                "success": False,
                "error": "sandbox worker produced no response",
                "stdout": "",
                "stderr": (res.stderr or "")[:_max_stderr_bytes()],
                "exit_code": 1,
                "worker_mode": True,
                "backend": "process",
                "run_id": run_id,
            }
            _audit("sandbox_execute_failed", backend="process", exit_code=1, error=out["error"], run_id=run_id)
            return out
        data = json.loads(resp.read_text(encoding="utf-8"))
        data.setdefault("worker_mode", True)
        data.setdefault("stdout", "")
        data.setdefault("stderr", "")
        data.setdefault("exit_code", 0 if data.get("success") else 1)
        data.setdefault("backend", "process")
        data.setdefault("run_id", run_id)
        _audit("sandbox_execute_done", backend="process", success=bool(data.get("success")), exit_code=data.get("exit_code", 0), run_id=run_id)
        return data
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


def _invoke_docker_worker(code: str, timeout: int, run_id: str) -> dict:
    preflight = validate_docker_backend()
    _audit("sandbox_preflight", backend="docker", ok=preflight.get("ok"), errors=preflight.get("errors"), warnings=preflight.get("warnings"), image=preflight.get("image"), rootless=preflight.get("docker", {}).get("rootless"), run_id=run_id)
    if not preflight.get("ok"):
        return {
            "success": False,
            "error": "; ".join(preflight.get("errors") or ["docker sandbox preflight failed"]),
            "stdout": "",
            "stderr": "\n".join(preflight.get("warnings") or []),
            "exit_code": 125,
            "worker_mode": True,
            "backend": "docker",
            "preflight": preflight,
        }
    base_dir = tempfile.mkdtemp(prefix="archillx_code_exec_docker_")
    _audit("sandbox_execute_start", backend="docker", timeout_s=timeout, image=_docker_image(), network=_docker_network_mode(), user=_docker_user(), run_id=run_id)
    try:
        run_dir = Path(base_dir)
        req, resp = _prepare_request(run_dir, code)
        worker_src = _worker_dir()
        args = [
            "docker", "run", "--rm",
            "--network", _docker_network_mode(),
            "--memory", _docker_memory_limit(),
            "--cpus", _docker_cpus(),
            "--pids-limit", _docker_pids_limit(),
            "--ulimit", "cpu=2:2",
            "--ulimit", "nofile=64:64",
            "--ulimit", "nproc=64:64",
            "--read-only",
            "--user", _docker_user(),
            "--security-opt", "no-new-privileges",
            "--security-opt", f"seccomp={_docker_seccomp_profile()}",
            "--cap-drop", "ALL",
            "--mount", f"type=bind,src={run_dir},dst=/sandbox/run",
            "--mount", f"type=bind,src={worker_src},dst=/sandbox/worker,readonly",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m",
            "-w", "/sandbox/run",
        ]
        if _docker_apparmor_profile():
            args.extend(["--security-opt", f"apparmor={_docker_apparmor_profile()}"])
        args.extend([
            _docker_image(),
            "python", "-I", "-S", "-B", "/sandbox/worker/sandbox_worker.py", "/sandbox/run/request.json", "/sandbox/run/response.json",
        ])
        res = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout + 2,
            stdin=subprocess.DEVNULL,
            env={"PATH": os.environ.get("PATH", "")},
        )
        if res.returncode != 0:
            stderr = (res.stderr or "")[:_max_stderr_bytes()]
            out = {
                "success": False,
                "error": f"docker sandbox exit {res.returncode}",
                "stdout": (res.stdout or "")[:_max_stdout_bytes()],
                "stderr": stderr,
                "exit_code": res.returncode,
                "worker_mode": True,
                "backend": "docker",
                "run_id": run_id,
                "policy": {
                    "require_network_none": require_network_none(),
                    "require_read_only_rootfs": require_read_only_rootfs(),
                    "require_cap_drop_all": require_cap_drop_all(),
                    "require_no_new_privileges": require_no_new_privileges(),
                    "user": _docker_user(),
                    "seccomp_profile": _docker_seccomp_profile(),
                    "apparmor_profile": _docker_apparmor_profile(),
                },
            }
            _audit("sandbox_execute_failed", backend="docker", exit_code=res.returncode, stderr=stderr[:200], run_id=run_id)
            return out
        if not resp.exists():
            out = {
                "success": False,
                "error": "docker sandbox produced no response",
                "stdout": (res.stdout or "")[:_max_stdout_bytes()],
                "stderr": (res.stderr or "")[:_max_stderr_bytes()],
                "exit_code": 1,
                "worker_mode": True,
                "backend": "docker",
                "run_id": run_id,
                "policy": {
                    "require_network_none": require_network_none(),
                    "require_read_only_rootfs": require_read_only_rootfs(),
                    "require_cap_drop_all": require_cap_drop_all(),
                    "require_no_new_privileges": require_no_new_privileges(),
                    "user": _docker_user(),
                    "seccomp_profile": _docker_seccomp_profile(),
                    "apparmor_profile": _docker_apparmor_profile(),
                },
            }
            _audit("sandbox_execute_failed", backend="docker", exit_code=1, error=out["error"], run_id=run_id)
            return out
        data = json.loads(resp.read_text(encoding="utf-8"))
        data.setdefault("worker_mode", True)
        data.setdefault("stdout", "")
        data.setdefault("stderr", "")
        data.setdefault("exit_code", 0 if data.get("success") else 1)
        data.setdefault("backend", "docker")
        data.setdefault("run_id", run_id)
        data.setdefault("policy", {
            "require_network_none": require_network_none(),
            "require_read_only_rootfs": require_read_only_rootfs(),
            "require_cap_drop_all": require_cap_drop_all(),
            "require_no_new_privileges": require_no_new_privileges(),
            "user": _docker_user(),
            "seccomp_profile": _docker_seccomp_profile(),
            "apparmor_profile": _docker_apparmor_profile(),
        })
        _audit("sandbox_execute_done", backend="docker", success=bool(data.get("success")), exit_code=data.get("exit_code", 0), run_id=run_id)
        return data
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


def _invoke_worker(code: str, timeout: int, run_id: str) -> dict:
    backend = _sandbox_backend()
    if backend == "docker":
        return _invoke_docker_worker(code, timeout, run_id)
    return _invoke_process_worker(code, timeout, run_id)


def run(inputs: dict) -> dict:
    backend = _sandbox_backend()
    run_id = uuid.uuid4().hex
    if not _is_enabled():
        out = {
            "error": "code_exec disabled by policy. Set ARCHILLX_ENABLE_CODE_EXEC=true to enable.",
            "stdout": "",
            "stderr": "code_exec disabled by policy",
            "exit_code": 1,
            "success": False,
            "worker_mode": True,
            "backend": backend,
            "run_id": run_id,
        }
        _audit("sandbox_denied", backend=backend, reason="disabled", run_id=run_id)
        return out

    code = str(inputs.get("code", ""))
    if not code:
        return {"error": "code required", "stdout": "", "stderr": "", "exit_code": 1, "success": False, "worker_mode": True, "backend": backend, "run_id": run_id}
    if len(code.encode("utf-8")) > _max_code_bytes():
        return {"error": f"code exceeds max allowed size ({_max_code_bytes()} bytes)", "stdout": "", "stderr": "", "exit_code": 1, "success": False, "worker_mode": True, "backend": backend, "run_id": run_id}

    timeout = max(1, min(int(inputs.get("timeout_s", 5)), 8))
    violation = _scan(code)
    if violation:
        _audit("sandbox_denied", backend=backend, reason="static_scan", violation=violation[:200], run_id=run_id)
        return {"error": violation, "stdout": "", "stderr": violation, "exit_code": 1, "success": False, "worker_mode": True, "backend": backend, "run_id": run_id}

    try:
        return _invoke_worker(code, timeout, run_id)
    except subprocess.TimeoutExpired:
        _audit("sandbox_execute_failed", backend=backend, exit_code=-1, error=f"timeout after {timeout}s", run_id=run_id)
        return {
            "error": f"timeout after {timeout}s",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "success": False,
            "worker_mode": True,
            "backend": backend,
            "run_id": run_id,
        }
    except Exception as e:
        _audit("sandbox_execute_failed", backend=backend, exit_code=-1, error=str(e)[:200])
        return {"error": str(e), "stdout": "", "stderr": "", "exit_code": -1, "success": False, "worker_mode": True, "backend": backend}
