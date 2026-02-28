# Delivery Manifest

## Core application
- `app/`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `docker-compose.prod.yml`

## Configuration and environment
- `.env.example`
- `.env.prod.example`
- `.env.prod` (sanitized deployment template; replace placeholder secrets before use)
- `configs/`

## Database and migrations
- `alembic.ini`
- `alembic/`
- `scripts/migrate.sh`
- `scripts/check_migration_state.py`

## Deployment assets
- `deploy/nginx/`
- `deploy/caddy/`
- `deploy/systemd/`
- `deploy/logrotate/`
- `deploy/docker/seccomp/`
- `deploy/apparmor/`
- `deploy/mysql/init/`

## Operations scripts
- `scripts/preflight_deploy.sh`
- `scripts/release_check.py`
- `scripts/release_check.sh`
- `scripts/rollback_check.py`
- `scripts/rollback_check.sh`
- `scripts/backup_stack.sh`
- `scripts/restore_stack.sh`
- `scripts/restore_drill.sh`
- `scripts/archive_audit.sh`
- `scripts/gate_summary.py`
- `scripts/gate_summary.sh`
- `scripts/verify_target_host.sh`

## Documentation
- `README.md`
- `DEPLOYMENT.md`
- `CHANGELOG.md`
- `RELEASE_NOTES_v0.44.0.md`
- `FINAL_RELEASE_CHECKLIST.md`
- `docs/METRICS_DASHBOARD.md`
- `docs/TELEMETRY_API.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/GATE_SUMMARY_DASHBOARD.md`
- `docs/SANDBOX_HOST_ENABLEMENT.md`
- `docs/RELEASE_ROLLBACK_RESTORE_RUNBOOK.md`
- `docs/LOCAL_PRODUCTION_VERIFICATION.md`

## Tests and smoke
- `tests/`
- `scripts/smoke_test_*.py`

## Evidence paths created at runtime
- `evidence/releases/`
- `evidence/dashboards/`
- `evidence/drills/`
- `evidence/archive/` (created and tracked with `.gitkeep` for archive pipeline readiness)
- `evidence/security_audit.jsonl`

## v69 system delivery portal
- `docs/SYSTEM_FINAL_DELIVERY.md`
- `docs/SYSTEM_DELIVERY_INDEX.md`
