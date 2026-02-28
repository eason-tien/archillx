
# Evolution Subsystem Overview (v62)

This document summarizes the Evolution subsystem as a standalone governable subsystem.

## Scope

The subsystem covers:

- inspection
- planning
- proposal generation
- upgrade guard
- baseline compare
- approval / reject / apply / rollback
- auto scheduling
- dashboard export
- evidence indexing and navigation

## Primary API entrypoints

- `GET /v1/evolution/subsystem`
- `POST /v1/evolution/subsystem/render`
- `GET /v1/evolution/summary`
- `GET /v1/evolution/evidence/index`

## Recommended users

### Operator
Start with:
- `/v1/evolution/summary`
- `/v1/evolution/evidence/index`

### Reviewer
Start with:
- `/v1/evolution/proposals/list`
- `/v1/evolution/dashboard/render`

### Approver
Start with:
- `/v1/evolution/actions/list`
- `/v1/evolution/summary`

## Evidence layout

All artifacts are stored under:

- `evidence/evolution/`

Key subdirectories:
- `inspections/`
- `plans/`
- `proposals/`
- `guards/`
- `baselines/`
- `actions/`
- `schedules/`
- `dashboards/`

## Subsystem bundle

`POST /v1/evolution/subsystem/render` creates a bundle with:

- JSON manifest
- Markdown overview
- HTML overview

This is intended as a handoff / review artifact for the subsystem as a whole.


- `docs/EVOLUTION_NAVIGATION.md`

- Navigation endpoints: `/v1/evolution/nav`, `/v1/evolution/nav/render`


- `docs/EVOLUTION_PORTAL.md`


## Portal home (v66)

The portal bundle now acts as the subsystem home page and groups entrypoints into operations, review/approval, evidence, dashboard, and runbook lanes.


- `docs/EVOLUTION_FINAL.md`


## Integration guide (v68)

See `docs/SYSTEM_EVOLUTION_INTEGRATION.md` for the integrated delivery and operating model with the main system.
