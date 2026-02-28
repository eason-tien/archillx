# ArcHillx Operations Runbook

This runbook is for operators, on-call engineers, and deployment owners running ArcHillx in a controlled environment.

---

## 1. Service scope

ArcHillx is expected to provide:
- API runtime on `/v1/*`
- liveness and readiness probes
- metrics and telemetry outputs
- audit evidence and audit query APIs
- backup / restore / restore-drill tooling
- release and rollback gates
- migration state checks

---

## 2. Critical endpoints

### Health and readiness
- `GET /v1/health`
- `GET /v1/live`
- `GET /v1/ready`
- `GET /v1/migration/state`

### Observability
- `GET /metrics`
- `GET /v1/metrics`
- `GET /v1/telemetry`
- `GET /v1/audit`
- `GET /v1/audit/summary`
- `GET /v1/audit/actions`
- `GET /v1/audit/decisions`

### Audit maintenance
- `POST /v1/audit/archive`
- `GET /v1/audit/export?format=json`
- `GET /v1/audit/export?format=jsonl`

---


## 2A. Linked release / rollback / restore runbook

For a single operator path that ties together release gate, rollback gate, gate summary, and restore drill, use:
- `docs/RELEASE_ROLLBACK_RESTORE_RUNBOOK.md`

Use that document when you need one checklist that spans:
- planned rollout
- degraded rollout with rollback decision
- restore validation or controlled restore execution

---

## 3. Daily checks

Run these at least once per day in pilot / production-like environments.

### API surface
1. `GET /v1/live` returns `200`
2. `GET /v1/ready` returns `ready`
3. `GET /v1/migration/state` returns `200` and `status=head`

### Control plane
1. Check `/v1/audit/summary`
2. Check `/v1/governor/config`
3. Check `/v1/telemetry`

### High-risk execution
If sandbox execution is enabled:
1. verify `ARCHILLX_ENABLE_CODE_EXEC=true` is intentional
2. verify backend is `docker`
3. verify sandbox image exists
4. verify no unusual spike in:
   - sandbox blocked
   - sandbox failed
   - skill access denied

---

## 4. Deployment runbook

### Before deploy
1. review `docs/RELEASE_ROLLBACK_RESTORE_RUNBOOK.md` if the change window may require rollback or restore decisions
2. update code and configuration
2. run release gate:

```bash
./scripts/release_check.sh --mode deploy --env-file .env.prod
```

3. confirm migration state is clean or upgrade is planned
4. verify backup exists for the target environment

### Deploy
1. apply migration if needed:

```bash
./scripts/migrate.sh upgrade head
```

2. start or update services:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

3. verify:
- `/v1/live`
- `/v1/ready`
- `/v1/migration/state`
- `/v1/metrics`
- `/v1/audit/summary`

### After deploy
1. watch error rate and readiness for 10 to 30 minutes
2. check audit summary for unexpected `BLOCKED` or `WARNED` spikes
3. if code execution is enabled, check sandbox decisions and backend split

---

## 5. Rollback runbook

### When to rollback
Use rollback when:
- readiness stays degraded after deploy
- migration state is inconsistent
- 5xx rate spikes and does not recover
- governor or sandbox failures make service unusable
- pilot users confirm a hard regression

### Before rollback
Review `docs/RELEASE_ROLLBACK_RESTORE_RUNBOOK.md` for the combined rollback / restore decision path.

Run rollback gate:

```bash
./scripts/rollback_check.sh --mode deploy --env-file .env.prod --backup-archive ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz
```

### Rollback steps
1. stop traffic or reduce exposure at proxy layer if needed
2. restore known-good DB/evidence backup if rollback requires data restore
3. downgrade application version / image
4. if schema changed, run migration rollback only if tested for this release
5. verify:
   - `/v1/live`
   - `/v1/ready`
   - `/v1/migration/state`
   - `/v1/audit/summary`

### After rollback
1. export evidence from `evidence/releases/rollback_check_*.json`
2. capture backup archive used
3. capture application image / commit / deployment time
4. record incident summary

---

## 6. Backup and restore runbook

### Backup
Manual backup:

```bash
./scripts/backup_stack.sh
```

Expected artifacts:
- MySQL dump
- evidence archive
- backup metadata

### Verify backup archive

```bash
python scripts/verify_backup_archive.py ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz --json
```

### Restore drill (safe default)
See also: `docs/RELEASE_ROLLBACK_RESTORE_RUNBOOK.md` for the linked operator flow.


```bash
./scripts/restore_drill.sh ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz
```

This should generate evidence under:
- `evidence/drills/`

### Controlled restore execution
Only in a rehearsal environment:

```bash
export RUN_RESTORE_DRILL=true
./scripts/restore_drill.sh ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz --execute
```

---

## 7. Audit operations runbook

### Archive audit file
Manual archive:

```bash
./scripts/archive_audit.sh
```

### Review audit trends
Check:
- `GET /v1/audit/summary`
- `GET /v1/audit/actions`
- `GET /v1/audit/decisions`

Look for spikes in:
- `sandbox_denied`
- `sandbox_execute_failed`
- `BLOCKED`
- `WARNED`
- unexpected `file_ops` access attempts

### Export audit records

```bash
curl "http://localhost:8000/v1/audit/export?format=jsonl"
```

Use JSONL export for incident evidence and external analysis.

---

## 8. Metrics and telemetry runbook

### Prometheus / dashboard source
- `/metrics`
- `/v1/metrics`

### JSON snapshot source
- `/v1/telemetry`

### What to watch first during an incident
1. HTTP 5xx rate
2. readiness status
3. governor blocked / warned counts
4. sandbox failures and backend split
5. top skill invocations
6. cron failures / blocked jobs

### If telemetry shows recent-window spikes
Use `history.windows.last_60s` and `last_300s` to compare:
- request rate
- blocked governor decisions
- sandbox failures
- skill failures
- cron failures

---

## 9. Migration runbook

### Check current state

```bash
./scripts/migrate.sh current
python scripts/check_migration_state.py
```

### Upgrade

```bash
./scripts/migrate.sh upgrade head
```

### Downgrade one revision

```bash
./scripts/migrate.sh downgrade -1
```

### On readiness failure caused by migration drift
1. call `/v1/migration/state`
2. compare `current` vs `head`
3. if behind, apply migration
4. if unknown, inspect DB connectivity and `alembic_version`

---

## 10. Sandbox / ACL runbook

### Recommended production posture
- keep `code_exec` disabled unless necessary
- if enabled, use `docker` backend only
- require ACL
- require non-root sandbox user
- require `network=none`
- require sandbox image preflight

### Investigate high-risk skill problems
Check:
- audit summary
- telemetry aggregate/history
- `/v1/skills` list
- sandbox backend setting
- ACL enabled status

### Typical failure modes
- `SKILL_ACCESS_DENIED`
- `SKILL_INPUT_INVALID`
- `code_exec disabled by policy`
- docker image missing
- sandbox preflight blocked

---

## 11. Evidence paths

Important evidence locations:
- `evidence/security_audit.jsonl`
- `evidence/archive/`
- `evidence/drills/`
- `evidence/releases/release_check_*.json`
- `evidence/releases/rollback_check_*.json`

These should be persisted off-container in production-like environments.

---

## 12. Recommended operator checklist

### Every deploy
- release gate passed
- migration state verified
- readiness green
- telemetry reachable
- audit summary reviewed

### Every rollback
- rollback gate passed
- backup archive verified
- restore drill evidence available
- post-rollback readiness green

### Every week
- review audit trends
- review top skill and cron activity
- verify backup creation succeeded
- verify audit archive is rotating

### Every month
- run restore drill
- review metrics dashboard and alert thresholds
- verify sandbox image and preflight policies



---

## 10. Sandbox host enablement runbook (v42)

Use this when docker code execution is enabled.

Primary reference:
- `docs/SANDBOX_HOST_ENABLEMENT.md`

### Minimum operator checklist
1. confirm the sandbox image exists
2. confirm the seccomp profile file exists on the host
3. if AppArmor is required, confirm the profile is loaded
4. confirm `.env.prod` points to the correct seccomp path / AppArmor profile
5. run `./scripts/preflight_deploy.sh --env-file .env.prod`
6. after rollout, verify `/v1/ready`, `/v1/telemetry`, and `/v1/audit/summary`

### Evidence to attach
- preflight output
- latest release gate evidence
- latest rollback gate evidence
- latest telemetry snapshot
- latest audit summary


## Evolution governance runbook (v54)

Use `docs/EVOLUTION_GOVERNANCE.md` when operating the self-evolution pipeline. Reviewers should inspect proposal/guard/baseline evidence before approval. Operators should ensure release and rollback gates remain green before apply or rollback actions.


## v55 Evolution dashboard summary

- API: `POST /v1/evolution/dashboard/render`
- Evidence output: `evidence/evolution/dashboards/evolution_summary_*.{json,md,html}`


## Linked evolution runbook (v57)

Use `docs/EVOLUTION_RUNBOOK.md` as the operator-facing linked flow for inspection → plan → proposal → guard → baseline → approve/reject → apply/rollback → auto-scheduler review.


## v58 Evolution dashboard docs

- Guide: `docs/EVOLUTION_DASHBOARD.md`
- Summary API: `GET /v1/evolution/summary`
- Render API: `POST /v1/evolution/dashboard/render`


- `docs/EVOLUTION_EVIDENCE.md`


- `docs/EVOLUTION_SUBSYSTEM.md`


- `docs/EVOLUTION_NAVIGATION.md`

- Navigation endpoints: `/v1/evolution/nav`, `/v1/evolution/nav/render`


- `docs/EVOLUTION_PORTAL.md`


## Integration guide (v68)

See `docs/SYSTEM_EVOLUTION_INTEGRATION.md` for the integrated delivery and operating model with the main system.


- `docs/ALERTING.md
- `docs/ALERTING_PRODUCTION_INTEGRATION.md``


## Alert receiver ownership

For owner mapping and receiver examples, see:

- `docs/ALERTING_RECEIVERS_AND_OWNERS.md
- webhook receiver payload flow now documented in the owner mapping guide`


- `docs/ALERT_WEBHOOK_CONSUMER_TEMPLATE.md`


- `deploy/alertmanager/examples/fastapi_consumer.py`
- `deploy/alertmanager/examples/flask_consumer.py`


- `deploy/alertmanager/examples/common_payload.py`


- Alert webhook consumer test examples:
  - `deploy/alertmanager/examples/test_fastapi_consumer_example.py`
  - `deploy/alertmanager/examples/test_flask_consumer_example.py`
