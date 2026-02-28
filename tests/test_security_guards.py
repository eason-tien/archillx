from app.skills.code_exec import run as run_code
from app.skills.file_ops import run as run_file
from app.security.skill_acl import check_skill_access, SkillAccessDenied


def test_code_exec_blocks_os_import():
    res = run_code({"code": "import os\nprint(1)"})
    assert res["success"] is False


def test_file_ops_blocks_outside_whitelist(tmp_path):
    res = run_file({"operation": "exists", "path": "/etc/passwd"})
    assert "error" in res


def test_skill_acl_denies_high_risk_anonymous():
    manifest = {"permissions": ["filesystem"], "acl": {"allow_sources": ["api"]}}
    try:
        check_skill_access("file_ops", manifest, {"source": "api", "role": "anonymous"})
        assert False
    except SkillAccessDenied:
        assert True
