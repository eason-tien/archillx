from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def sandbox_backend() -> str:
    value = os.getenv("ARCHILLX_SANDBOX_BACKEND", "process").strip().lower()
    return value if value in {"process", "docker"} else "process"


def docker_image() -> str:
    return os.getenv("ARCHILLX_SANDBOX_DOCKER_IMAGE", "archillx-sandbox:latest").strip() or "archillx-sandbox:latest"


def docker_network_mode() -> str:
    return os.getenv("ARCHILLX_SANDBOX_DOCKER_NETWORK", "none").strip() or "none"


def docker_user() -> str:
    return os.getenv("ARCHILLX_SANDBOX_DOCKER_USER", "65534:65534").strip() or "65534:65534"


def docker_seccomp_profile() -> str:
    return os.getenv("ARCHILLX_SANDBOX_DOCKER_SECCOMP_PROFILE", "deploy/docker/seccomp/archillx-seccomp.json").strip() or "deploy/docker/seccomp/archillx-seccomp.json"


def docker_apparmor_profile() -> str:
    return os.getenv("ARCHILLX_SANDBOX_DOCKER_APPARMOR_PROFILE", "").strip()


def require_rootless() -> bool:
    return os.getenv("ARCHILLX_SANDBOX_REQUIRE_ROOTLESS", "false").strip().lower() in {"1", "true", "yes", "on"}


def require_network_none() -> bool:
    return os.getenv("ARCHILLX_SANDBOX_REQUIRE_NETWORK_NONE", "true").strip().lower() in {"1", "true", "yes", "on"}


def require_image_present() -> bool:
    return os.getenv("ARCHILLX_SANDBOX_REQUIRE_IMAGE_PRESENT", "true").strip().lower() in {"1", "true", "yes", "on"}


def require_non_root_user() -> bool:
    return os.getenv("ARCHILLX_SANDBOX_REQUIRE_NON_ROOT_USER", "true").strip().lower() in {"1", "true", "yes", "on"}


def require_seccomp_profile() -> bool:
    return os.getenv("ARCHILLX_SANDBOX_REQUIRE_SECCOMP_PROFILE", "true").strip().lower() in {"1", "true", "yes", "on"}


def require_apparmor_profile() -> bool:
    return os.getenv("ARCHILLX_SANDBOX_REQUIRE_APPARMOR_PROFILE", "false").strip().lower() in {"1", "true", "yes", "on"}


def require_read_only_rootfs() -> bool:
    return os.getenv("ARCHILLX_SANDBOX_REQUIRE_READ_ONLY_ROOTFS", "true").strip().lower() in {"1", "true", "yes", "on"}


def require_cap_drop_all() -> bool:
    return os.getenv("ARCHILLX_SANDBOX_REQUIRE_CAP_DROP_ALL", "true").strip().lower() in {"1", "true", "yes", "on"}


def require_no_new_privileges() -> bool:
    return os.getenv("ARCHILLX_SANDBOX_REQUIRE_NO_NEW_PRIVILEGES", "true").strip().lower() in {"1", "true", "yes", "on"}


def _run(args: list[str], timeout: int = 8) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, env={"PATH": os.environ.get("PATH", "")})


def docker_cli_available() -> bool:
    return shutil.which("docker") is not None


def docker_image_exists(image: str | None = None) -> bool:
    image = image or docker_image()
    if not docker_cli_available():
        return False
    res = _run(["docker", "image", "inspect", image], timeout=12)
    return res.returncode == 0


def _seccomp_profile_exists(path: str | None = None) -> bool:
    profile = (path or docker_seccomp_profile()).strip()
    return bool(profile) and Path(profile).exists()


def docker_info_summary() -> dict[str, Any]:
    if not docker_cli_available():
        return {"available": False, "error": "docker CLI not available"}
    res = _run(["docker", "info", "--format", "{{json .}}"], timeout=12)
    if res.returncode != 0:
        return {
            "available": True,
            "reachable": False,
            "error": (res.stderr or res.stdout or "docker info failed").strip()[:400],
        }
    try:
        data = json.loads(res.stdout)
    except Exception:
        return {
            "available": True,
            "reachable": False,
            "error": "docker info output was not valid JSON",
        }
    sec = data.get("SecurityOptions") or []
    sec_text = " ".join(str(x) for x in sec).lower()
    rootless = bool(data.get("Rootless")) or ("rootless" in sec_text)
    return {
        "available": True,
        "reachable": True,
        "rootless": rootless,
        "security_options": sec,
        "server_version": data.get("ServerVersion"),
        "cgroup_driver": data.get("CgroupDriver"),
    }


def validate_docker_backend() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    info = docker_info_summary()
    image = docker_image()
    network = docker_network_mode()
    user = docker_user()
    seccomp_profile = docker_seccomp_profile()
    apparmor_profile = docker_apparmor_profile()

    if not info.get("available"):
        errors.append("docker CLI not available")
    elif not info.get("reachable", False):
        errors.append(info.get("error") or "docker daemon not reachable")

    if require_network_none() and network != "none":
        errors.append("docker sandbox policy requires ARCHILLX_SANDBOX_DOCKER_NETWORK=none")
    elif network != "none":
        warnings.append(f"docker network mode is {network!r}, not 'none'")

    if require_non_root_user() and (not user or user.split(':', 1)[0] in {'0', 'root'}):
        errors.append("docker sandbox policy requires non-root ARCHILLX_SANDBOX_DOCKER_USER")

    if info.get("available") and info.get("reachable") and require_rootless() and not info.get("rootless", False):
        errors.append("docker sandbox policy requires rootless Docker")
    elif info.get("available") and info.get("reachable") and not info.get("rootless", False):
        warnings.append("docker daemon does not appear rootless")

    image_present = docker_image_exists(image) if info.get("available") and info.get("reachable") else False
    if require_image_present() and info.get("available") and info.get("reachable") and not image_present:
        errors.append(f"docker sandbox image not present: {image}")

    if require_seccomp_profile():
        if not seccomp_profile:
            errors.append("docker sandbox policy requires ARCHILLX_SANDBOX_DOCKER_SECCOMP_PROFILE")
        elif not _seccomp_profile_exists(seccomp_profile):
            errors.append(f"docker sandbox seccomp profile not found: {seccomp_profile}")
    elif seccomp_profile and not _seccomp_profile_exists(seccomp_profile):
        warnings.append(f"configured seccomp profile not found: {seccomp_profile}")

    if require_apparmor_profile() and not apparmor_profile:
        errors.append("docker sandbox policy requires ARCHILLX_SANDBOX_DOCKER_APPARMOR_PROFILE")
    elif apparmor_profile and apparmor_profile.lower() == "unconfined":
        errors.append("docker sandbox AppArmor profile must not be 'unconfined'")

    if not require_read_only_rootfs():
        warnings.append("read-only rootfs requirement disabled")
    if not require_cap_drop_all():
        warnings.append("cap-drop-all requirement disabled")
    if not require_no_new_privileges():
        warnings.append("no-new-privileges requirement disabled")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "backend": "docker",
        "image": image,
        "network": network,
        "user": user,
        "image_present": image_present,
        "seccomp_profile": seccomp_profile,
        "seccomp_profile_present": _seccomp_profile_exists(seccomp_profile) if seccomp_profile else False,
        "apparmor_profile": apparmor_profile,
        "requirements": {
            "rootless": require_rootless(),
            "network_none": require_network_none(),
            "image_present": require_image_present(),
            "non_root_user": require_non_root_user(),
            "seccomp_profile": require_seccomp_profile(),
            "apparmor_profile": require_apparmor_profile(),
            "read_only_rootfs": require_read_only_rootfs(),
            "cap_drop_all": require_cap_drop_all(),
            "no_new_privileges": require_no_new_privileges(),
        },
        "docker": info,
    }
