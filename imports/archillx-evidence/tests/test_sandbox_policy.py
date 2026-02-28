import os

from app.security import sandbox_policy as sp


def test_validate_docker_backend_rejects_root_user(monkeypatch):
    monkeypatch.setenv("ARCHILLX_SANDBOX_DOCKER_USER", "0:0")
    monkeypatch.setenv("ARCHILLX_SANDBOX_REQUIRE_NON_ROOT_USER", "true")
    monkeypatch.setattr(sp, "docker_info_summary", lambda: {"available": True, "reachable": True, "rootless": True})
    monkeypatch.setattr(sp, "docker_image_exists", lambda image=None: True)
    result = sp.validate_docker_backend()
    assert result["ok"] is False
    assert any("non-root" in e.lower() for e in result["errors"])


def test_validate_docker_backend_accepts_hardened_profile(monkeypatch):
    monkeypatch.setenv("ARCHILLX_SANDBOX_DOCKER_NETWORK", "none")
    monkeypatch.setenv("ARCHILLX_SANDBOX_DOCKER_USER", "65534:65534")
    monkeypatch.setenv("ARCHILLX_SANDBOX_REQUIRE_NETWORK_NONE", "true")
    monkeypatch.setenv("ARCHILLX_SANDBOX_REQUIRE_NON_ROOT_USER", "true")
    monkeypatch.setenv("ARCHILLX_SANDBOX_REQUIRE_ROOTLESS", "false")
    monkeypatch.setattr(sp, "docker_info_summary", lambda: {"available": True, "reachable": True, "rootless": True})
    monkeypatch.setattr(sp, "docker_image_exists", lambda image=None: True)
    result = sp.validate_docker_backend()
    assert result["ok"] is True
    assert result["errors"] == []



def test_validate_docker_backend_rejects_missing_seccomp_profile(monkeypatch):
    monkeypatch.setenv("ARCHILLX_SANDBOX_DOCKER_NETWORK", "none")
    monkeypatch.setenv("ARCHILLX_SANDBOX_DOCKER_USER", "65534:65534")
    monkeypatch.setenv("ARCHILLX_SANDBOX_REQUIRE_SECCOMP_PROFILE", "true")
    monkeypatch.setenv("ARCHILLX_SANDBOX_DOCKER_SECCOMP_PROFILE", "/no/such/profile.json")
    monkeypatch.setattr(sp, "docker_info_summary", lambda: {"available": True, "reachable": True, "rootless": True})
    monkeypatch.setattr(sp, "docker_image_exists", lambda image=None: True)
    result = sp.validate_docker_backend()
    assert result["ok"] is False
    assert any("seccomp profile" in e.lower() for e in result["errors"])


def test_validate_docker_backend_rejects_unconfined_apparmor(monkeypatch, tmp_path):
    profile = tmp_path / "seccomp.json"
    profile.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ARCHILLX_SANDBOX_DOCKER_NETWORK", "none")
    monkeypatch.setenv("ARCHILLX_SANDBOX_DOCKER_USER", "65534:65534")
    monkeypatch.setenv("ARCHILLX_SANDBOX_REQUIRE_SECCOMP_PROFILE", "true")
    monkeypatch.setenv("ARCHILLX_SANDBOX_DOCKER_SECCOMP_PROFILE", str(profile))
    monkeypatch.setenv("ARCHILLX_SANDBOX_REQUIRE_APPARMOR_PROFILE", "true")
    monkeypatch.setenv("ARCHILLX_SANDBOX_DOCKER_APPARMOR_PROFILE", "unconfined")
    monkeypatch.setattr(sp, "docker_info_summary", lambda: {"available": True, "reachable": True, "rootless": True})
    monkeypatch.setattr(sp, "docker_image_exists", lambda image=None: True)
    result = sp.validate_docker_backend()
    assert result["ok"] is False
    assert any("apparmor" in e.lower() for e in result["errors"])
