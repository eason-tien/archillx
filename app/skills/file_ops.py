"""ArcHillx — File Operations Skill (path whitelist safety)"""
from __future__ import annotations

import os
from pathlib import Path


def _whitelist() -> list[Path]:
    defaults = ["./evidence", "./data", "./output", "/tmp"]
    extra = [p.strip() for p in
             os.getenv("ARCHELI_FILE_WHITELIST", "").split(",") if p.strip()]
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
    op = inputs.get("operation", "").lower()
    path_str = inputs.get("path", "")
    if not op or not path_str:
        return {"error": "operation and path required"}
    target = Path(path_str)

    if op not in ("list", "exists", "read") and not _allowed(target):
        return {"error": f"Path '{path_str}' not in allowed whitelist."}

    try:
        if op == "read":
            return {"content": target.read_text("utf-8"),
                    "size": target.stat().st_size, "path": str(target)}
        elif op == "write":
            c = inputs.get("content", "")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(c, "utf-8")
            return {"written": len(c), "path": str(target)}
        elif op == "list":
            entries = [{"name": e.name, "is_dir": e.is_dir(),
                        "size": e.stat().st_size if e.is_file() else 0}
                       for e in sorted(target.iterdir())] if target.is_dir() else []
            return {"entries": entries, "count": len(entries)}
        elif op == "delete":
            if target.is_file():
                target.unlink()
                return {"deleted": str(target)}
            elif target.is_dir():
                import shutil; shutil.rmtree(str(target))
                return {"deleted": str(target), "type": "directory"}
            return {"error": f"'{path_str}' not found"}
        elif op == "exists":
            return {"exists": target.exists(), "is_file": target.is_file(),
                    "is_dir": target.is_dir()}
        elif op == "mkdir":
            target.mkdir(parents=True, exist_ok=True)
            return {"created": str(target)}
        else:
            return {"error": f"unknown operation: {op}"}
    except PermissionError as e:
        return {"error": f"Permission denied: {e}"}
    except Exception as e:
        return {"error": str(e)}
