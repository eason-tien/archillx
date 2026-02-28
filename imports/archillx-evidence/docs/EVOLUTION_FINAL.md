# Evolution Final Overview

This document is the final overview page for the Evolution subsystem.

## Purpose

Use this page when you need a single handoff-level reference that links:

- summary and pipeline status
- dashboard / portal / navigation outputs
- evidence index
- proposal and action query surfaces
- governance and runbooks
- delivery and handoff notes

## Primary API entrypoints

- `GET /v1/evolution/final`
- `POST /v1/evolution/final/render`
- `GET /v1/evolution/summary`
- `GET /v1/evolution/portal`
- `GET /v1/evolution/nav`
- `GET /v1/evolution/evidence/index`

## Rendered bundle

`POST /v1/evolution/final/render` writes a bundle under `evidence/evolution/dashboards/` in:

- JSON
- Markdown
- HTML

## Recommended usage

1. Open the final bundle after a review window.
2. Check pending approval / actionable / guard pass / regression rate.
3. Jump into portal, dashboard and evidence index from there.
4. Use governance + runbook docs before approve/apply/rollback.


## Integration guide (v68)

See `docs/SYSTEM_EVOLUTION_INTEGRATION.md` for the integrated delivery and operating model with the main system.
