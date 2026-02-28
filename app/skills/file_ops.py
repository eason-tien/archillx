"""ArcHillx — File Operations Skill (path whitelist safety)"""
from __future__ import annotations

import os
from pathlib import Path

_MAX_READ_BYTES = 2 * 1024 * 1024
_MAX_LIST_ENTRIES = 1000
_ALLOWED_OPS = {"read", "write", "list", "delete", "exists", "mkdir"}


def _whitelist() -> list[Path]:
    defaults = ["./evidence", "./data", "./output", "/tmp"]
    # Keep backward compatibility for the historical typo while supporting the
    # correct env var name.
    raw_extra = os.getenv("ARCHILLX_FILE_WHITELIST", "") or os.getenv("ARCHELI_FILE_WHITELIST", "")
    extra = [p.strip() for p in raw_extra.split(",") if p.strip()]
    return [Path(p).resolve() for p in defaults + extra]


def _allowed(path: Path) -> bool:
    resolved = path.resolve()
    for base in _whitelist():
        try:
            resolved.relative_to(base)
            return True
        except ValueError:
            continue
    return False


def run(inputs: dict) -> dict:
    op = inputs.get("operation", "").lower().strip()
    path_str = inputs.get("path", "")
    if not op or not path_str:
        return {"error": "operation and path required"}
    if op not in _ALLOWED_OPS:
        return {"error": f"unknown operation: {op}"}

    target = Path(path_str)
    if not _allowed(target):
        return {"error": f"Path '{path_str}' not in allowed whitelist."}

    try:
        if op == "read":
            if not target.exists() or not target.is_file():
                return {"error": f"'{path_str}' not found or not a file"}
            size = target.stat().st_size
            if size > _MAX_READ_BYTES:
                return {"error": f"file too large to read safely ({size} bytes > {_MAX_READ_BYTES})"}
            return {"content": target.read_text("utf-8"), "size": size, "path": str(target)}

        if op == "write":
            content = str(inputs.get("content", ""))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, "utf-8")
            return {"written": len(content), "path": str(target)}

        if op == "list":
            if not target.exists() or not target.is_dir():
                return {"entries": [], "count": 0, "truncated": False}
            items = sorted(target.iterdir())
            truncated = len(items) > _MAX_LIST_ENTRIES
            limited = items[:_MAX_LIST_ENTRIES]
            entries = [
                {
                    "name": e.name,
                    "is_dir": e.is_dir(),
                    "size": e.stat().st_size if e.is_file() else 0,
                }
                for e in limited
            ]
            return {
                "entries": entries,
                "count": len(entries),
                "truncated": truncated,
            }

        if op == "delete":
            if target.is_file():
                target.unlink()
                return {"deleted": str(target)}
            if target.is_dir():
                import shutil
                shutil.rmtree(str(target))
                return {"deleted": str(target), "type": "directory"}
            return {"error": f"'{path_str}' not found"}

        if op == "exists":
            return {"exists": target.exists(), "is_file": target.is_file(), "is_dir": target.is_dir()}

        if op == "mkdir":
            target.mkdir(parents=True, exist_ok=True)
            return {"created": str(target)}

        return {"error": f"unknown operation: {op}"}
    except PermissionError as e:
        return {"error": f"Permission denied: {e}"}
    except UnicodeDecodeError:
        return {"error": "file is not valid utf-8 text"}
    except Exception as e:
        return {"error": str(e)}
