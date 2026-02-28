# ArcHillx Sandbox Host Enablement Guide

This guide explains how to enable and validate the **Docker sandbox hardening assets** shipped with ArcHillx on the host side.

It complements:
- `DEPLOYMENT.md` — rollout and production deployment
- `docs/OPERATIONS_RUNBOOK.md` — day-2 operations and incident handling
- `deploy/docker/seccomp/archillx-seccomp.json` — seccomp profile
- `deploy/apparmor/archillx-sandbox.profile` — AppArmor profile template

---

## 1. Scope

This guide applies when you enable:
- `ARCHILLX_ENABLE_CODE_EXEC=true`
- `ARCHILLX_SANDBOX_BACKEND=docker`

If code execution remains disabled, these host steps are optional.

---

## 2. Security model

ArcHillx Docker sandbox is designed to run with these restrictions together:

- non-root container user
- no network access
- read-only root filesystem
- `cap-drop=ALL`
- `no-new-privileges`
- seccomp profile
- optional AppArmor profile
- bounded tmpfs and resource limits

Host-side enablement matters because the container runtime must actually enforce these controls. The application can preflight-check them, but the host must still provide the files and kernel features.

---

## 3. Required host prerequisites

### Linux host
Recommended baseline:
- modern Linux kernel
- Docker Engine installed and operational
- AppArmor available if you want AppArmor enforcement
- seccomp support enabled in Docker / kernel

### Docker checks
Verify Docker is available:

```bash
docker version
```

Verify the daemon is reachable:

```bash
docker info
```

Optional but recommended:
- rootless Docker
- dedicated host or node pool for sandbox workloads

---

## 4. Enable the seccomp profile

Shipped asset:
- `deploy/docker/seccomp/archillx-seccomp.json`

Recommended path on host:

```bash
sudo mkdir -p /opt/archillx/seccomp
sudo cp deploy/docker/seccomp/archillx-seccomp.json /opt/archillx/seccomp/
```

Set in `.env.prod`:

```env
ARCHILLX_SANDBOX_DOCKER_SECCOMP_PROFILE=/opt/archillx/seccomp/archillx-seccomp.json
ARCHILLX_SANDBOX_REQUIRE_SECCOMP_PROFILE=true
```

### Validate
- file exists
- Docker can access it
- ArcHillx preflight reports `seccomp_profile_present=true`

---

## 5. Enable the AppArmor profile (optional but recommended)

Shipped asset:
- `deploy/apparmor/archillx-sandbox.profile`

Recommended path on host:

```bash
sudo mkdir -p /etc/apparmor.d
sudo cp deploy/apparmor/archillx-sandbox.profile /etc/apparmor.d/
```

Load it:

```bash
sudo apparmor_parser -r /etc/apparmor.d/archillx-sandbox.profile
```

Set in `.env.prod`:

```env
ARCHILLX_SANDBOX_DOCKER_APPARMOR_PROFILE=archillx-sandbox.profile
ARCHILLX_SANDBOX_REQUIRE_APPARMOR_PROFILE=true
```

### Validate
Check profile status:

```bash
sudo aa-status | grep archillx-sandbox.profile || true
```

If your environment does not support AppArmor, leave:

```env
ARCHILLX_SANDBOX_REQUIRE_APPARMOR_PROFILE=false
```

Do **not** set the profile to `unconfined`.

---

## 6. Recommended production sandbox settings

Use this as the hardened baseline in `.env.prod`:

```env
ARCHILLX_ENABLE_CODE_EXEC=true
ARCHILLX_SANDBOX_BACKEND=docker
ARCHILLX_SANDBOX_DOCKER_IMAGE=archillx-sandbox:latest
ARCHILLX_SANDBOX_DOCKER_NETWORK=none
ARCHILLX_SANDBOX_DOCKER_USER=65534:65534
ARCHILLX_SANDBOX_REQUIRE_NETWORK_NONE=true
ARCHILLX_SANDBOX_REQUIRE_IMAGE_PRESENT=true
ARCHILLX_SANDBOX_REQUIRE_NON_ROOT_USER=true
ARCHILLX_SANDBOX_REQUIRE_SECCOMP_PROFILE=true
ARCHILLX_SANDBOX_REQUIRE_APPARMOR_PROFILE=false
ARCHILLX_SANDBOX_REQUIRE_READ_ONLY_ROOTFS=true
ARCHILLX_SANDBOX_REQUIRE_CAP_DROP_ALL=true
ARCHILLX_SANDBOX_REQUIRE_NO_NEW_PRIVILEGES=true
```

Use AppArmor only after validating host support.

---

## 7. Rootless Docker guidance

Recommended for stronger isolation where operationally practical.

### Check rootless mode

```bash
docker info | grep -i rootless || true
```

If you require it, set:

```env
ARCHILLX_SANDBOX_REQUIRE_ROOTLESS=true
```

If your environment cannot run rootless Docker yet, keep it `false` and record the exception in your deployment notes.

---

## 8. Host validation flow

Run these checks in order:

### A. Build the sandbox image

```bash
./scripts/build_sandbox_image.sh
```

### B. Run deployment preflight

```bash
./scripts/preflight_deploy.sh --env-file .env.prod
```

### C. Check migration + readiness

```bash
curl -fsS http://127.0.0.1:8000/v1/migration/state
curl -fsS http://127.0.0.1:8000/v1/ready
```

### D. Validate telemetry / audit after sandbox enablement

Review:
- `/v1/metrics`
- `/v1/telemetry`
- `/v1/audit/summary`

Look specifically for:
- sandbox denied / failed spikes
- unexpected `BLOCKED` or `WARNED`
- backend split not matching `docker`

---

## 9. Recommended operational checks after enabling sandbox

After enabling docker code execution, confirm:

1. `sandbox_backend_docker_total` increases
2. `sandbox_backend_process_total` remains zero or expected
3. `sandbox_decision_BLOCKED_total` does not spike unexpectedly
4. `/v1/ready` remains `ready`
5. release gate and rollback gate evidence remain green

---

## 10. Troubleshooting

### Seccomp profile missing
Symptom:
- docker sandbox preflight fails
- readiness may degrade depending on configuration

Actions:
1. verify the file path in `.env.prod`
2. confirm the file exists on host
3. restart the service after correcting the path

### AppArmor profile not active
Symptom:
- preflight warns or blocks when `ARCHILLX_SANDBOX_REQUIRE_APPARMOR_PROFILE=true`

Actions:
1. confirm AppArmor exists on host
2. load the profile with `apparmor_parser`
3. verify with `aa-status`
4. if unsupported, set the requirement to `false` and document the exception

### Sandbox still using process backend
Symptom:
- telemetry shows `sandbox.by_backend.process`

Actions:
1. confirm `ARCHILLX_SANDBOX_BACKEND=docker`
2. confirm code execution is enabled
3. verify docker image is present
4. inspect startup env and service file

### Docker backend blocked by preflight
Actions:
1. inspect `/v1/audit` and `/v1/audit/summary`
2. review `scripts/preflight_deploy.sh`
3. check `.env.prod` sandbox requirement flags
4. confirm host files and runtime features match policy

---

## 11. Evidence to retain

For change records and security review, keep:
- release gate evidence
- rollback gate evidence
- latest `/v1/audit/summary`
- latest `/v1/telemetry` snapshot
- seccomp profile path used
- AppArmor profile name used (if enabled)
- any approved deviations, such as AppArmor disabled or rootless not yet enabled

---

## 12. Recommended rollout sequence

1. enable docker backend with seccomp profile
2. keep AppArmor optional for first rollout
3. validate metrics / telemetry / audit
4. enable AppArmor in the next controlled rollout if host support is ready
5. consider rootless requirement after host validation is complete

This phased approach reduces rollout risk while still moving toward a harder sandbox posture.
