from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.skill_manager import skill_manager
from app.skills.file_ops import run as file_ops_run
from app.config import settings


def main() -> int:
    print("SMOKE=START")
    print(f"APP={settings.app_name} VERSION={settings.app_version}")
    skill_manager.startup()
    names = [s["name"] for s in skill_manager.list_skills()]
    print("SKILLS=", ",".join(sorted(names)))

    tmp = Path("/tmp/archillx_smoke_v2.txt")
    result = file_ops_run({"operation": "write", "path": str(tmp), "content": "ok"})
    print("FILE_WRITE=", result)
    result = file_ops_run({"operation": "read", "path": str(tmp)})
    print("FILE_READ=", result)
    blocked = file_ops_run({"operation": "exists", "path": "/etc/passwd"})
    print("FILE_BLOCK=", blocked)
    print("SMOKE=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
