# Changelog

## v1.0.0 - Final release consolidation

This release consolidates the work completed across v1-v43 into a production-oriented delivery baseline.

### Highlights
- Agent runtime with OODA loop, goals, sessions, memory, cron, and model routing
- Security hardening for `file_ops` and `code_exec`
- Process and Docker sandbox backends with seccomp/AppArmor assets and policy checks
- Audit APIs, summaries, exports, governance dashboards, and release/rollback gates
- Readiness/liveness probes, metrics, telemetry aggregates and historical windows
- Deployment assets, runbooks, migration scripts, restore drills, and release/rollback automation
- Extensive test suite and smoke scripts for core, security, API, migration, and operations flows

### Final packaging additions
- `VERSION`
- `CHANGELOG.md`
- `RELEASE_NOTES_v0.44.0.md` (historical filename retained for bundle compatibility)
- `DELIVERY_MANIFEST.md`
- `FINAL_RELEASE_CHECKLIST.md`

### Recommended deployment level
- Suitable for controlled internal deployment / pilot environments
- Not recommended for unrestricted public exposure of high-risk skills without additional organizational controls
