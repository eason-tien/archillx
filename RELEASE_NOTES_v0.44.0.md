# ArcHillx v1.0.0 Release Notes

## Release identity
- Version: `1.0.0`
- Packaging goal: final release consolidation
- Note: filename retained as `RELEASE_NOTES_v0.44.0.md` for compatibility with existing bundle tooling
- Intended use: controlled deployment, pilot rollout, internal productionization baseline

## What is included

### Runtime and API
- FastAPI service
- `/v1/agent/run` runtime entry
- sessions, goals, memory, cron, planner/proactive/notifications hooks
- health/live/ready endpoints

### Security and governance
- API key and admin token auth
- skill ACL enforcement
- sandbox execution policies
- audit recording, summary, export, and governance views
- release and rollback gate automation

### Operations and deployment
- Docker / docker-compose assets
- production env templates
- Nginx / Caddy / systemd assets
- backup / restore / restore drill scripts
- migration scripts and Alembic setup
- metrics dashboards and runbooks

## Known deployment stance
This release is ready for:
- local development
- single-node deployment
- controlled internal pilot / intranet use

This release should still be treated cautiously for:
- public exposure of `file_ops`
- public exposure of `code_exec`
- multitenant hostile environments without additional perimeter controls

## Recommended pre-release checks
1. `./scripts/release_check.sh --mode deploy --env-file .env.prod`
2. `./scripts/rollback_check.sh --mode deploy --env-file .env.prod --backup-archive <archive>`
3. `./scripts/migrate.sh upgrade head`
4. `python scripts/smoke_test_v37_release_check.py`
5. `python scripts/smoke_test_v38_rollback_check.py`

## Evidence and artifacts
- release gate evidence: `evidence/releases/`
- audit evidence: `evidence/security_audit.jsonl`
- dashboards: `evidence/dashboards/`
- drills: `evidence/drills/`

## Bundle-specific notes
- `.env.prod` is included as a sanitized deployment template and must be replaced with real secrets before deployment.
- `backups/archillx_backup_*.tar.gz` may be included as a sanitized sample archive for rollback-gate dry-runs in offline bundle review environments.
- Migration commands still require the real `alembic` package to be installed from `requirements.txt`.

## Bundle verification snapshot
- `pytest tests -q`: passed (`177 passed`)
- `python scripts/smoke_test_v37_release_check.py`: passed
- `python scripts/smoke_test_v38_rollback_check.py`: passed
- `python scripts/smoke_test_v40_sandbox_hardening.py`: passed
- `python scripts/release_check.py --mode deploy --env-file .env.prod --skip-preflight --skip-compose`: passed
- `python scripts/rollback_check.py --mode deploy --env-file .env.prod --backup-archive backups/archillx_backup_*.tar.gz --skip-migration-check --skip-migration-history`: passed

## Formal target-host verification assets
- `docs/LOCAL_PRODUCTION_VERIFICATION.md`
- `scripts/verify_target_host.sh`
- checklist now separates bundle checks from real deployment-host checks
