from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.skills.file_ops import run as file_run
from app.skills.code_exec import run as code_run
from app.security.skill_acl import check_skill_access, SkillAccessDenied


def main() -> None:
    r1 = file_run({"operation": "exists", "path": "/etc/passwd"})
    assert "error" in r1

    r2 = code_run({"code": "print(1)"})
    assert r2["success"] is False
    assert "disabled" in (r2["error"] or "")

    denied = False
    try:
        check_skill_access(
            "code_exec",
            {"permissions": ["exec"], "acl": {"allow_sources": ["api"]}},
            {"source": "api", "role": "anonymous"},
        )
    except SkillAccessDenied:
        denied = True
    assert denied
    print("OK_V5_SECURITY_SMOKE")


if __name__ == "__main__":
    main()
