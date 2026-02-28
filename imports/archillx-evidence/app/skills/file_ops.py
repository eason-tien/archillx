"""ArcHillx — File Operations Skill (path whitelist safety)"""
from __future__ import annotations

import os
from pathlib import Path


READ_ONLY_OPS = {"list", "exists", "read"}
WRITE_OPS = {"write", "delete", "mkdir"}
ALLOWED_OPS = READ_ONLY_OPS | WRITE_OPS


def _whitelist() -> list[Path]:
    defaults = ["./evidence", "./data", "./output", "/tmp"]
    extra_raw = os.getenv("ARCHILLX_FILE_WHITELIST", os.getenv("ARCHELI_FILE_WHITELIST", ""))
    extra = [p.strip() for p in extra_raw.split(",") if p.strip()]
    return [Path(p).expanduser().resolve() for p in defaults + extra]


def _max_read_bytes() -> int:
    return max(1024, int(os.getenv("ARCHILLX_FILE_MAX_READ_BYTES", str(1024 * 1024))))


def _max_write_bytes() -> int:
    return max(1024, int(os.getenv("ARCHILLX_FILE_MAX_WRITE_BYTES", str(1024 * 1024))))


def _allowed(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    for base in _whitelist():
        try:
            resolved.relative_to(base)
            return True
        except ValueError:
            continue
    return False


def _has_symlink_component(path: Path) -> bool:
    abs_path = path.expanduser().absolute()
    current = Path(abs_path.anchor or "/")
    for part in abs_path.parts[1:] if abs_path.is_absolute() else abs_path.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            return True
    return path.exists() and path.is_symlink()


def _guard_path(target: Path, path_str: str, op: str) -> dict | None:
    if _has_symlink_component(target):
        return {"error": f"Path '{path_str}' rejected because symlink traversal is not allowed."}
    if not _allowed(target):
        return {"error": f"Path '{path_str}' not in allowed whitelist."}
    if op == "delete" and target.expanduser().resolve() in _whitelist():
        return {"error": f"Refusing to delete whitelist root: '{path_str}'"}
    return None


def run(inputs: dict) -> dict:
    op = str(inputs.get("operation", "")).lower().strip()
    path_str = str(inputs.get("path", "")).strip()
    if not op or not path_str:
        return {"error": "operation and path required"}
    if op not in ALLOWED_OPS:
        return {"error": f"unknown operation: {op}"}

    target = Path(path_str)
    guard_error = _guard_path(target, path_str, op)
    if guard_error:
        return guard_error

    try:
        if op == "read":
            if not target.exists():
                return {"error": f"'{path_str}' not found"}
            if not target.is_file():
                return {"error": f"'{path_str}' is not a file"}
            size = target.stat().st_size
            if size > _max_read_bytes():
                return {"error": f"File too large to read safely ({size} bytes > {_max_read_bytes()} bytes)."}
            return {"content": target.read_text("utf-8"),
                    "size": size, "path": str(target.resolve())}
        elif op == "write":
            c = str(inputs.get("content", ""))
            b = c.encode("utf-8")
            if len(b) > _max_write_bytes():
                return {"error": f"Content too large to write safely ({len(b)} bytes > {_max_write_bytes()} bytes)."}
            target.parent.mkdir(parents=True, exist_ok=True)
            if _has_symlink_component(target.parent):
                return {"error": f"Path '{path_str}' rejected because parent symlink traversal is not allowed."}
            target.write_text(c, "utf-8")
            return {"written": len(c), "path": str(target.resolve())}
        elif op == "list":
            if not target.exists():
                return {"error": f"'{path_str}' not found"}
            if not target.is_dir():
                return {"error": f"'{path_str}' is not a directory"}
            entries = [{"name": e.name, "is_dir": e.is_dir(),
                        "size": e.stat().st_size if e.is_file() else 0}
                       for e in sorted(target.iterdir())]
            return {"entries": entries, "count": len(entries), "path": str(target.resolve())}
        elif op == "delete":
            if target.is_file():
                target.unlink()
                return {"deleted": str(target.resolve())}
            elif target.is_dir():
                import shutil
                shutil.rmtree(str(target))
                return {"deleted": str(target.resolve()), "type": "directory"}
            return {"error": f"'{path_str}' not found"}
        elif op == "exists":
            return {"exists": target.exists(), "is_file": target.is_file(),
                    "is_dir": target.is_dir(), "path": str(target.resolve())}
        elif op == "mkdir":
            target.mkdir(parents=True, exist_ok=True)
            return {"created": str(target.resolve())}
        return {"error": f"unknown operation: {op}"}
    except UnicodeDecodeError as e:
        return {"error": f"Only utf-8 text files are supported: {e}"}
    except PermissionError as e:
        return {"error": f"Permission denied: {e}"}
    except FileNotFoundError as e:
        return {"error": f"Path not found: {e}"}
    except IsADirectoryError as e:
        return {"error": f"Expected file but got directory: {e}"}
    except Exception as e:
        return {"error": str(e)}
