# ArcHillx Deployment Checklist

## Recommended deployment tier

### Safe now
- Local development
- Single-node Docker deployment
- Internal pilot / limited-access staging

### Not recommended yet
- Public internet exposure with unrestricted `file_ops` / `code_exec`

## Minimum production-ish settings

```env
APP_ENV=production
LOG_LEVEL=INFO
DB_TYPE=mysql
API_KEY=change-me
ADMIN_TOKEN=change-me-admin
ENABLE_SKILL_ACL=true
ENABLE_SKILL_VALIDATION=true
ENABLE_RATE_LIMIT=true
RATE_LIMIT_PER_MIN=120
HIGH_RISK_RATE_LIMIT_PER_MIN=15
ARCHILLX_ENABLE_CODE_EXEC=false
```

## If code execution must be enabled

```env
ARCHILLX_ENABLE_CODE_EXEC=true
ARCHILLX_SANDBOX_BACKEND=docker
ARCHILLX_SANDBOX_DOCKER_IMAGE=archillx-sandbox:latest
ARCHILLX_SANDBOX_DOCKER_NETWORK=none
ARCHILLX_SANDBOX_DOCKER_USER=65534:65534
ARCHILLX_SANDBOX_REQUIRE_NETWORK_NONE=true
ARCHILLX_SANDBOX_REQUIRE_IMAGE_PRESENT=true
ARCHILLX_SANDBOX_REQUIRE_NON_ROOT_USER=true
```

## Preflight checks
- `GET /v1/health`
- `GET /v1/live`
- `GET /v1/ready`
- `GET /v1/audit/summary`
- `GET /v1/governor/config`

## Recommended reverse proxy controls
- TLS termination
- request body limit
- IP allow-list for admin endpoints
- request timeout
- access logs enabled

## Persistence
- database volume / managed DB
- `evidence/` mounted to persistent storage
- regular backup for DB + audit evidence

## Suggested rollout order
1. Deploy with `code_exec` off
2. Confirm `/v1/ready` returns `ready`
3. Verify `pytest tests -q`
4. Enable pilot users only
5. Review `/v1/audit` and `/v1/audit/summary`
6. Only then consider enabling docker sandbox code execution


## Productionization Additions (v22)

- `/v1/metrics` and `/metrics` expose Prometheus-style plaintext metrics.
- `/v1/telemetry` exposes JSON telemetry when `ENABLE_TELEMETRY=true`.
- `/v1/audit/archive` rotates the current `security_audit.jsonl` into `evidence/archive/`.
- Alembic skeleton is included (`alembic.ini`, `alembic/`, `alembic/versions/`).
- `AUDIT_FILE_MAX_BYTES` controls JSONL audit file rotation threshold.


## Deployment Assets (v23)

Included files:
- `docker-compose.prod.yml` — MySQL + ArcHillx + Nginx production-oriented stack
- `.env.prod.example` — starter production env template
- `deploy/nginx/archillx.conf` — reverse proxy sample with health and metrics handling
- `docs/METRICS_DASHBOARD.md` — metric map, panel layout, and alert guidance
- `docs/TELEMETRY_API.md` — snapshot / aggregate / history JSON structure and usage
- `deploy/grafana/archillx-dashboard.json` — starter Grafana dashboard JSON
- `deploy/caddy/Caddyfile` — alternative reverse proxy sample
- `deploy/systemd/archillx.service` — systemd wrapper for docker compose
- `deploy/systemd/archillx-sandbox-image.service` — sandbox image build helper
- `scripts/preflight_deploy.sh` — deployment preflight checker

Suggested rollout:
1. `.env.prod` is included as a sanitized template for gate readiness
2. replace placeholder secrets and DB credentials before deploy
3. `./scripts/preflight_deploy.sh`
4. `./scripts/build_sandbox_image.sh` (if `code_exec` will be enabled)
5. `docker compose -f docker-compose.prod.yml up -d --build`
6. verify `/v1/live`, `/v1/ready`, `/v1/metrics`, `/v1/audit/summary`


## Ops Assets (v24)

Included files:
- `docker-compose.prod.override.example.yml` — optional TLS/resource/logging override sample
- `deploy/nginx/archillx.tls.conf` — HTTPS reverse proxy sample
- `deploy/logrotate/archillx` — logrotate sample for logs + audit jsonl
- `scripts/backup_stack.sh` — MySQL + evidence backup helper
- `scripts/restore_stack.sh` — backup restore helper
- `scripts/archive_audit.sh` — invoke audit archive endpoint
- `deploy/systemd/archillx-backup.service` / `.timer` — daily backup timer
- `deploy/systemd/archillx-audit-archive.service` / `.timer` — hourly audit archive timer

Suggested ops rollout:
1. review the included sanitized `.env.prod` and replace placeholder secrets / backup paths
2. optionally copy `docker-compose.prod.override.example.yml` to `docker-compose.prod.override.yml`
3. install `deploy/logrotate/archillx` under `/etc/logrotate.d/`
4. enable `archillx-backup.timer` and `archillx-audit-archive.timer`
5. test `./scripts/backup_stack.sh` and `./scripts/archive_audit.sh` manually before go-live


## Database migration

Before first startup or after schema changes, run:

```bash
./scripts/migrate.sh upgrade head
```

Check migration state:

```bash
./scripts/migrate.sh current
./scripts/migrate.sh history
```


## Restore drill

Use `scripts/verify_backup_archive.py` to validate backup archives and `scripts/restore_drill.sh <archive>` to produce a restore-drill evidence report. Add `--execute` with `RUN_RESTORE_DRILL=true` only in a controlled rehearsal environment.

Included ops timers now also provide `deploy/systemd/archillx-restore-drill.service` and `.timer` for periodic restore rehearsal verification.


## Rollback gate automation (v38)

Included files:
- `scripts/rollback_check.py` — automated rollback readiness gate
- `scripts/rollback_check.sh` — shell wrapper
- `evidence/releases/` — JSON rollback gate reports

Recommended usage:

```bash
./scripts/rollback_check.sh --mode ci
./scripts/rollback_check.sh --mode deploy --env-file .env.prod --backup-archive ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz
```

What it checks:
- rollback assets exist
- `compileall`
- `pytest tests -q`
- shell syntax for backup/restore scripts
- migration state check
- migration history is readable
- backup archive passes validation
- restore drill dry-run succeeds
- JSON evidence is written to `evidence/releases/rollback_check_*.json`

## Release gate automation (v37)

Included files:
- `scripts/release_check.py` — automated release gate
- `scripts/release_check.sh` — shell wrapper
- `evidence/releases/` — JSON release gate reports

Recommended usage:

```bash
./scripts/release_check.sh --mode ci
./scripts/release_check.sh --mode deploy --env-file .env.prod
```

What it checks:
- required deployment files exist
- `compileall`
- `pytest tests -q`
- production compose config parses
- deploy preflight passes
- migration state check passes
- sandbox image exists when docker code execution is enabled


## Operations runbook (v39)

Included file:
- `docs/OPERATIONS_RUNBOOK.md` — operator/on-call runbook for deploy, rollback, backup, restore drill, audit operations, telemetry, migration, sandbox/ACL

Recommended usage:
1. keep `DEPLOYMENT.md` for setup and rollout
2. use `docs/OPERATIONS_RUNBOOK.md` during day-2 operations and incidents
3. attach release / rollback gate evidence files to change records
4. review telemetry + audit summary after every deploy and rollback


## v40 sandbox hardening

Additional docker sandbox hardening controls are available:
- `ARCHILLX_SANDBOX_DOCKER_SECCOMP_PROFILE`
- `ARCHILLX_SANDBOX_DOCKER_APPARMOR_PROFILE`
- `ARCHILLX_SANDBOX_REQUIRE_SECCOMP_PROFILE`
- `ARCHILLX_SANDBOX_REQUIRE_APPARMOR_PROFILE`
- `ARCHILLX_SANDBOX_REQUIRE_READ_ONLY_ROOTFS`
- `ARCHILLX_SANDBOX_REQUIRE_CAP_DROP_ALL`
- `ARCHILLX_SANDBOX_REQUIRE_NO_NEW_PRIVILEGES`

Shipped assets:
- `deploy/docker/seccomp/archillx-seccomp.json`
- `deploy/apparmor/archillx-sandbox.profile`

Host-side enablement and validation are documented in:
- `docs/SANDBOX_HOST_ENABLEMENT.md`

Recommended usage:
1. copy the seccomp profile to a stable host path (for example `/opt/archillx/seccomp/`)
2. optionally install the AppArmor profile on supported Linux hosts
3. point `.env.prod` at those host-side paths / profile names
4. run `./scripts/preflight_deploy.sh --env-file .env.prod` before rollout
5. after rollout, verify `/v1/ready`, `/v1/telemetry`, and `/v1/audit/summary`


## Gate summary dashboard (v41)

After running release / rollback gates, generate a unified summary:

```bash
./scripts/gate_summary.sh --limit 20
```

Artifacts are written under `evidence/dashboards/` as JSON / Markdown / HTML.
Refer to `docs/GATE_SUMMARY_DASHBOARD.md` for operator usage.

## Release / rollback / restore linked runbook (v43)

Use `docs/RELEASE_ROLLBACK_RESTORE_RUNBOOK.md` when you want one operator path that joins together:
- `release_check`
- `rollback_check`
- `gate_summary`
- `restore_drill`

Recommended usage:
1. run release gate before rollout
2. generate gate summary
3. if rollout degrades, switch to rollback gate
4. if rollback is insufficient, validate and execute restore only through the controlled restore path

This complements `DEPLOYMENT.md` setup guidance and `docs/OPERATIONS_RUNBOOK.md` day-2 operations guidance.


## Final release handoff (v44)

For final delivery, review:
- `VERSION`
- `CHANGELOG.md`
- `RELEASE_NOTES_v0.44.0.md`
- `DELIVERY_MANIFEST.md`
- `FINAL_RELEASE_CHECKLIST.md`

Recommended last-mile sequence:
1. run release gate
2. run rollback gate
3. verify migration state
4. verify backup archive + restore drill
5. archive gate summary evidence


## Evolution
- docs/EVOLUTION_DESIGN.md


## Evolution upgrade guard (v47)

This release adds an upgrade guard stage for evolution proposals, including compileall, pytest, smoke, release gate, rollback gate, and migration checks.


## Evolution baseline compare (v48)

Before approving a self-generated proposal, run the evolution baseline compare API to detect obvious regressions in readiness, migration state, HTTP 5xx, skill failures, sandbox blocked events, governor blocks, and gate failures.


## v50 auto proposal scheduling

- `ENABLE_EVOLUTION_AUTO=true` enables scheduled evolution cycles.
- `EVOLUTION_AUTO_CYCLE_CRON` controls the cycle schedule.
- `POST /v1/evolution/schedule/run` triggers one full automatic cycle.
- Low-risk proposals can automatically enter guard when `EVOLUTION_AUTO_GUARD_LOW_RISK=true`.


## Evolution governance guide (v54)

For reviewer / approver / operator responsibilities and the proposal approval flow, see `docs/EVOLUTION_GOVERNANCE.md`. Use it together with `docs/EVOLUTION_DESIGN.md` and the linked operations runbooks when enabling self-evolution workflows in a controlled environment.


## Evolution runbook (v57)

For day-2 operation of the Evolution subsystem, including review, guard, baseline, approval, apply, rollback, and auto-scheduler oversight, see `docs/EVOLUTION_RUNBOOK.md`.


## v58 Evolution dashboard docs

- Guide: `docs/EVOLUTION_DASHBOARD.md`
- Summary API: `GET /v1/evolution/summary`
- Render API: `POST /v1/evolution/dashboard/render`


- `docs/EVOLUTION_SUBSYSTEM.md`


- `docs/EVOLUTION_NAVIGATION.md`

- Navigation endpoints: `/v1/evolution/nav`, `/v1/evolution/nav/render`


- `docs/EVOLUTION_PORTAL.md`


## Evolution portal home (v66)

Use the portal bundle when handing off the subsystem to operators or reviewers. The HTML output is structured as a multi-section home page rather than a flat list of links.


- `docs/EVOLUTION_FINAL.md`


## Main system + evolution integration (v68)

See `docs/SYSTEM_EVOLUTION_INTEGRATION.md` for the integrated delivery and operating model across the core runtime and the evolution subsystem.

## v69 system delivery portal
- `docs/SYSTEM_FINAL_DELIVERY.md`
- `docs/SYSTEM_DELIVERY_INDEX.md`


## v70 additions

- `/ui` management console skeleton
- proposal patch artifact bundle (`patch.diff`, `pr_draft.md`, `tests_to_add.md`, `rollout_notes.md`, `risk_assessment.json`)


## v73 patch artifact templates

Patch artifacts now also include `pr_title.txt` and `commit_message.txt` templates alongside `patch.diff`, `pr_draft.md`, `tests_to_add.md`, and `rollout_notes.md`.


- `docs/ALERTING.md
- `docs/ALERTING_PRODUCTION_INTEGRATION.md``

- `deploy/prometheus/docker-compose.alerting.example.yml`


## Alerting receiver mapping

- `docs/ALERTING_RECEIVERS_AND_OWNERS.md
- webhook receiver payload flow now documented in the owner mapping guide`


- `docs/ALERT_WEBHOOK_CONSUMER_TEMPLATE.md`


- `deploy/alertmanager/examples/fastapi_consumer.py`
- `deploy/alertmanager/examples/flask_consumer.py`


- `deploy/alertmanager/examples/common_payload.py`


- Alert webhook consumer test examples:
  - `deploy/alertmanager/examples/test_fastapi_consumer_example.py`
  - `deploy/alertmanager/examples/test_flask_consumer_example.py`

## Formal target-host verification (v113)

Use `docs/LOCAL_PRODUCTION_VERIFICATION.md` for the real deployment host. That document turns the release bundle into a concrete operator path and should be executed top-to-bottom during rollout.

New helper:
- `scripts/verify_target_host.sh` — validates host tools, migration prerequisites, and runtime endpoints on the deployment machine

Recommended order on the target host:
1. replace placeholder values in `.env.prod`
2. `./scripts/preflight_deploy.sh`
3. `./scripts/release_check.sh --mode deploy --env-file .env.prod`
4. `./scripts/migrate.sh upgrade head`
5. `docker compose -f docker-compose.prod.yml up -d --build`
6. `./scripts/verify_target_host.sh --env-file .env.prod --base-url http://127.0.0.1:8000`
7. create a fresh backup and run rollback / restore-drill validation
8. `./scripts/gate_summary.sh --limit 20`

This separates **bundle verification** from **real host verification** so the checklist can be completed honestly.
