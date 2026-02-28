# ArcHillx Release / Rollback / Restore Linked Runbook

This document ties together the **release gate**, **rollback gate**, and **restore drill** flows into one operator path.

Use it when you need one runbook that answers:
- **Can we deploy?**
- **Can we roll back safely?**
- **Can we restore evidence and data if rollback is not enough?**

---

## 1. Decision flow

### A. Planned release
1. Verify recent backup exists.
2. Run release gate:

```bash
./scripts/release_check.sh --mode deploy --env-file .env.prod
```

3. Generate gate summary:

```bash
./scripts/gate_summary.sh --limit 20
```

4. If release gate passes and rollback assets are healthy, proceed.

### B. Release degraded after rollout
1. Check `/v1/ready`, `/v1/migration/state`, `/v1/audit/summary`, `/v1/telemetry`.
2. If issue is recoverable quickly, stabilize in place.
3. If not recoverable, enter rollback path.

### C. Rollback path
1. Run rollback gate:

```bash
./scripts/rollback_check.sh --mode deploy --env-file .env.prod --backup-archive ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz
```

2. Confirm rollback evidence passes.
3. Roll back application and, only when required and already tested, roll back schema.
4. Re-check `/v1/live`, `/v1/ready`, `/v1/migration/state`.

### D. Restore path
Use restore when rollback alone cannot recover a consistent state, for example:
- bad data already persisted
- migration cannot be safely reversed in-place
- evidence or audit continuity must be restored from backup

Run a dry-run first:

```bash
./scripts/restore_drill.sh ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz
```

Only execute restore in a controlled rehearsal or approved incident workflow:

```bash
export RUN_RESTORE_DRILL=true
./scripts/restore_drill.sh ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz --execute
```

---

## 2. Operator checklists

### Release checklist
- [ ] recent backup archive exists
- [ ] `release_check` evidence exists and passed
- [ ] `gate_summary` shows stable release pass rate
- [ ] migration state is `head`
- [ ] sandbox image exists if docker sandbox is enabled
- [ ] post-deploy observation window defined

### Rollback checklist
- [ ] rollback archive path selected
- [ ] `rollback_check` evidence exists and passed
- [ ] migration rollback decision reviewed
- [ ] proxy / traffic reduction plan ready if needed
- [ ] post-rollback health verification steps assigned

### Restore checklist
- [ ] backup archive validated with `verify_backup_archive.py`
- [ ] dry-run restore evidence generated
- [ ] restore target environment approved
- [ ] `RUN_RESTORE_DRILL=true` set only for controlled execution
- [ ] post-restore readiness and audit review defined

---

## 3. Evidence map

### Release evidence
- `evidence/releases/release_check_*.json`
- `evidence/dashboards/gate_summary_*.json`
- `evidence/dashboards/gate_summary_*.md`
- `evidence/dashboards/gate_summary_*.html`

### Rollback evidence
- `evidence/releases/rollback_check_*.json`
- gate summary artifacts above

### Restore evidence
- `evidence/drills/restore_drill_*.json`

### Audit / telemetry evidence to review around every change
- `GET /v1/audit/summary`
- `GET /v1/telemetry`
- `GET /v1/migration/state`
- `GET /v1/ready`

---

## 4. Recommended sequence for controlled changes

### Standard change window
1. create fresh backup
2. run release gate
3. generate gate summary
4. deploy
5. observe readiness / telemetry / audit summary
6. if healthy, close change
7. if unhealthy, run rollback gate and execute rollback path
8. if rollback is insufficient, move to restore path

### Incident change window
1. stabilize traffic if needed
2. verify current readiness / migration / telemetry state
3. choose rollback vs restore
4. generate and attach evidence for whichever path is taken
5. record final evidence bundle in incident notes

---

## 5. Quick commands

### Release
```bash
./scripts/release_check.sh --mode deploy --env-file .env.prod
./scripts/gate_summary.sh --limit 20
```

### Rollback
```bash
./scripts/rollback_check.sh --mode deploy --env-file .env.prod --backup-archive ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz
./scripts/gate_summary.sh --limit 20
```

### Restore validation
```bash
python scripts/verify_backup_archive.py ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz --json
./scripts/restore_drill.sh ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz
```

### Post-action checks
```bash
curl http://localhost:8000/v1/ready
curl http://localhost:8000/v1/migration/state
curl http://localhost:8000/v1/audit/summary
curl http://localhost:8000/v1/telemetry
```

---

## 6.5 Target-host execution helper

When the bundle is moved onto the real deployment machine, run:

```bash
./scripts/verify_target_host.sh --env-file .env.prod --base-url http://127.0.0.1:8000
```

This helper checks:
- host tools (`python3`, `curl`, `docker`, `docker compose`)
- Alembic presence
- `preflight_deploy`
- migration commands
- migration state
- runtime endpoints (`/v1/live`, `/v1/ready`, `/v1/metrics`, `/v1/telemetry`, `/v1/audit/summary`, `/v1/migration/state`)

If the service is not started yet, use `--skip-endpoints` for the pre-start phase and re-run without it after rollout.

## 6. Relationship with other docs
- Deployment baseline: `DEPLOYMENT.md`
- Day-2 operations: `docs/OPERATIONS_RUNBOOK.md`
- Gate dashboard: `docs/GATE_SUMMARY_DASHBOARD.md`
- Sandbox host enablement: `docs/SANDBOX_HOST_ENABLEMENT.md`
