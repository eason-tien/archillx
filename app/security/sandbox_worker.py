from __future__ import annotations

import ast
import contextlib
import io
import json
import math
import random
import re
import statistics
import sys
import traceback
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

_ALLOWED_IMPORTS = {
    "math": math,
    "statistics": statistics,
    "random": random,
    "re": re,
    "json": json,
    "datetime": __import__("datetime"),
    "itertools": __import__("itertools"),
    "functools": __import__("functools"),
    "collections": __import__("collections"),
    "string": __import__("string"),
    "fractions": __import__("fractions"),
    "decimal": __import__("decimal"),
}
_BLOCKED_NAMES = {
    "eval", "exec", "compile", "open", "input", "help", "breakpoint",
    "globals", "locals", "vars", "dir", "getattr", "setattr", "delattr",
    "__import__", "exit", "quit",
}
_BLOCKED_MODULE_PREFIXES = (
    "os", "sys", "subprocess", "socket", "pathlib", "shutil", "resource", "signal",
    "ctypes", "multiprocessing", "threading", "asyncio", "importlib", "urllib", "requests",
)


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = (name or "").split(".")[0]
    if root not in _ALLOWED_IMPORTS:
        raise ImportError(f"Import of '{name}' is not allowed.")
    return _ALLOWED_IMPORTS[root]


def _safe_builtins() -> dict:
    allowed = {
        "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict, "enumerate": enumerate,
        "filter": filter, "float": float, "int": int, "len": len, "list": list, "map": map,
        "max": max, "min": min, "pow": pow, "print": print, "range": range, "reversed": reversed,
        "round": round, "set": set, "slice": slice, "sorted": sorted, "str": str, "sum": sum,
        "tuple": tuple, "zip": zip, "Exception": Exception, "ValueError": ValueError,
        "TypeError": TypeError, "Decimal": Decimal, "Fraction": Fraction,
        "datetime": datetime, "date": date, "time": time, "timedelta": timedelta, "timezone": timezone,
        "__import__": _safe_import,
    }
    return allowed


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


def _limit_output(s: str, max_len: int) -> tuple[str, bool]:
    if len(s) <= max_len:
        return s, False
    return s[:max_len], True


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    req_path = Path(sys.argv[1])
    resp_path = Path(sys.argv[2])
    payload = json.loads(req_path.read_text(encoding="utf-8"))
    code = str(payload.get("code", ""))
    max_stdout = int(payload.get("max_stdout", 4096))
    max_stderr = int(payload.get("max_stderr", 2048))
    violation = _scan(code)
    if violation:
        resp_path.write_text(json.dumps({
            "success": False, "error": violation, "stdout": "", "stderr": violation,
            "exit_code": 1, "worker_mode": True,
        }, ensure_ascii=False), encoding="utf-8")
        return 0

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    globals_dict = {"__builtins__": _safe_builtins(), "__name__": "__main__"}
    locals_dict = {}

    try:
        compiled = compile(code, "<sandboxed>", "exec")
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            exec(compiled, globals_dict, locals_dict)
        stdout, trunc_out = _limit_output(stdout_buf.getvalue(), max_stdout)
        stderr, trunc_err = _limit_output(stderr_buf.getvalue(), max_stderr)
        result = {
            "success": True,
            "error": None,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": 0,
            "truncated": trunc_out or trunc_err,
            "worker_mode": True,
        }
    except BaseException as e:
        tb = "".join(traceback.format_exception_only(type(e), e)).strip()
        stderr = stderr_buf.getvalue()
        stderr = (stderr + ("\n" if stderr else "") + tb).strip()
        stderr, trunc_err = _limit_output(stderr, max_stderr)
        result = {
            "success": False,
            "error": str(e),
            "stdout": "",
            "stderr": stderr,
            "exit_code": 1,
            "truncated": trunc_err,
            "worker_mode": True,
        }
    resp_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
