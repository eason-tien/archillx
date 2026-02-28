# ArcHillx Local Production Verification

Use this on the **real deployment host** after you have replaced placeholder values in `.env.prod`.

This document is intentionally operational: run it top-to-bottom and keep the terminal output or screenshots in your change record.

---

## 1. Preconditions

Confirm these first:
- the bundle is unpacked on the target host
- `.env.prod` contains real secrets and DB credentials
- Docker and Docker Compose are installed
- Python dependencies from `requirements.txt` are installed
- the target database is reachable

Recommended shell setup:

```bash
cd /path/to/archillx
python3 -m pip install -r requirements.txt
cp -n .env.prod.example .env.prod
# edit .env.prod and replace all placeholder values before continuing
```

---

## 2. Static deployment checks

```bash
./scripts/preflight_deploy.sh
./scripts/release_check.sh --mode deploy --env-file .env.prod
```

Expected result:
- preflight returns `[OK] preflight complete`
- release gate writes a JSON report under `evidence/releases/`

---

## 3. Migration checks

```bash
./scripts/migrate.sh current
./scripts/migrate.sh upgrade head
python3 ./scripts/check_migration_state.py .env.prod
```

Expected result:
- `upgrade head` completes without Alembic error
- `check_migration_state.py` reports current matches head

If Alembic is missing, install dependencies first and re-run this section.

---

## 4. Bring up the stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

If you use an override file:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d --build
```

---

## 5. Runtime endpoint verification

### One-shot helper

```bash
./scripts/verify_target_host.sh --env-file .env.prod --base-url http://127.0.0.1:8000
```

### Manual endpoint verification

```bash
curl http://127.0.0.1:8000/v1/live
curl http://127.0.0.1:8000/v1/ready
curl http://127.0.0.1:8000/v1/metrics
curl http://127.0.0.1:8000/v1/telemetry
curl http://127.0.0.1:8000/v1/audit/summary
curl http://127.0.0.1:8000/v1/migration/state
```

Expected result:
- all endpoints return HTTP 200
- `/v1/ready` reports ready
- `/v1/migration/state` shows aligned / head state

---

## 6. Sandbox hardening verification

Only required if `ARCHILLX_ENABLE_CODE_EXEC=true` and docker sandboxing is used.

Check these items:
- `ARCHILLX_SANDBOX_DOCKER_IMAGE` exists on the host
- seccomp profile path exists on the host filesystem
- AppArmor profile is installed or explicitly documented as unavailable
- docker sandbox runs as non-root and with network disabled if required

Recommended checks:

```bash
docker image inspect archillx-sandbox:latest
ls -l deploy/docker/seccomp/archillx-seccomp.json
sudo apparmor_status | grep archillx || true
python3 scripts/smoke_test_v40_sandbox_hardening.py
```

---

## 7. Backup / rollback readiness

Create a real backup before go-live:

```bash
./scripts/backup_stack.sh
latest_archive="$(ls -1t backups/archillx_backup_*.tar.gz | head -1)"
python3 scripts/verify_backup_archive.py --json "$latest_archive"
./scripts/rollback_check.sh --mode deploy --env-file .env.prod --backup-archive "$latest_archive"
./scripts/restore_drill.sh "$latest_archive"
```

Expected result:
- backup verify succeeds
- rollback gate succeeds
- restore drill dry-run writes evidence under `evidence/drills/`

---

## 8. Observability and handoff

Generate gate summary:

```bash
./scripts/gate_summary.sh --limit 20
```

Then confirm:
- latest `evidence/releases/release_check_*.json` exists
- latest `evidence/releases/rollback_check_*.json` exists
- latest `evidence/dashboards/gate_summary_*.html` exists
- deployment owner is recorded
- rollback owner is recorded

---

## 9. Change record template

Capture the following in your deployment ticket or ops record:
- host name / environment
- deploy timestamp
- release version
- migration result
- release gate evidence path
- rollback gate evidence path
- backup archive path
- restore drill evidence path
- deployment owner
- rollback owner

---

## 10. Minimum go-live exit criteria

You should not mark the deployment complete until all items below are true:
- `release_check` passed on the target host
- migration state is aligned at head
- runtime endpoints are healthy
- rollback gate passed using a real backup archive
- restore drill dry-run evidence exists
- gate summary was generated and reviewed
