# Evolution Portal

The evolution portal is the unified entry index for evidence, dashboard, runbook, governance, and subsystem resources.

## Primary API entrypoints

- `GET /v1/evolution/portal`
- `POST /v1/evolution/portal/render`
- `GET /v1/evolution/nav`
- `GET /v1/evolution/summary`
- `GET /v1/evolution/subsystem`
- `GET /v1/evolution/evidence/index`

## Portal blocks

- API entrypoints
- evidence entrypoints
- dashboard entrypoints
- runbook entrypoints
- recommended flows
- latest navigation
- pipeline snapshot

## Operator usage

Use the portal when you need a single navigation surface that links dashboard views, evidence drill-down, governance docs, and operational runbooks.

## Multi-section HTML home (v66)

The portal HTML bundle is now organized into lanes:

- Overview & quick actions
- Operations lane
- Review & approval lane
- Evidence lane
- Dashboard lane
- Runbook lane

This makes the portal more usable as a subsystem landing page during review windows and operator handoff.


- `docs/EVOLUTION_FINAL.md`
