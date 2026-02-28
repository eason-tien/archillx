# Final Release Checklist

## Bundle packaging and identity
- [x] Confirm `VERSION` matches intended release (`1.0.0`)
- [x] Review `CHANGELOG.md` and `RELEASE_NOTES_v0.44.0.md`
- [x] Ensure `.env.prod` is prepared from `.env.prod.example` (sanitized placeholders; replace before deploy)
- [x] Include deployment / rollback / restore docs in bundle
- [x] Include target-host verification helper: `scripts/verify_target_host.sh`
- [x] Include archive readiness path: `evidence/archive/`

## Bundle-verified quality gates
- [x] Run `pytest tests -q` (bundle verification: `177 passed`)
- [x] Run `./scripts/release_check.sh --mode deploy --env-file .env.prod` (bundle verification used `--skip-preflight --skip-compose`)
- [x] Run `./scripts/rollback_check.sh --mode deploy --env-file .env.prod --backup-archive <archive>` (bundle verification used sanitized sample archive and skipped migration-dependent checks)
- [x] Run `python scripts/smoke_test_v40_sandbox_hardening.py`
- [x] Run `python scripts/smoke_test_v37_release_check.py`
- [x] Run `python scripts/smoke_test_v38_rollback_check.py`
- [x] Confirm `scripts/migrate.sh` and `scripts/check_migration_state.py` are present and documented
- [x] Confirm release / rollback runbook links are present in docs

## Target-host migration verification
- [ ] Run `./scripts/migrate.sh current`
- [ ] Run `./scripts/migrate.sh upgrade head`
- [ ] Confirm `/v1/migration/state` returns aligned status
- [ ] Record migration evidence path or terminal capture in change ticket

## Target-host sandbox and security verification
- [ ] Validate seccomp profile path on host filesystem
- [ ] Validate AppArmor profile path or documented exception
- [ ] Confirm high-risk skills are ACL-gated in deployed config
- [ ] Confirm Docker sandbox image exists if `code_exec` is enabled

## Target-host observability verification
- [ ] Confirm `/v1/live`, `/v1/ready`, `/v1/metrics`, `/v1/telemetry`
- [ ] Confirm dashboard import works
- [ ] Confirm audit summary and export endpoints respond
- [ ] Generate and review gate summary artifacts in `evidence/dashboards/`

## Backup and rollback verification
- [x] Produce a fresh backup archive (sanitized sample archive included for bundle dry-run)
- [x] Verify archive with `python scripts/verify_backup_archive.py --json <archive>`
- [x] Run restore drill dry-run
- [ ] Validate a real production backup archive on the target host
- [ ] Attach latest rollback evidence JSON to change record

## Release handoff
- [ ] Attach delivery zip
- [x] Attach release notes (included in bundle)
- [x] Attach gate evidence paths (bundle evidence directories included)
- [ ] Record deployment owner and rollback owner
- [ ] Complete `docs/LOCAL_PRODUCTION_VERIFICATION.md` execution record on target host

## v69 system delivery portal
- `docs/SYSTEM_FINAL_DELIVERY.md`
- `docs/SYSTEM_DELIVERY_INDEX.md`
