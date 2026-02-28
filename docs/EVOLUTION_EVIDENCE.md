# Evolution Evidence Index & Navigation

This guide explains the evidence index and navigation views for the evolution subsystem.

## API

- `GET /v1/evolution/evidence/index` — return a grouped index of evidence kinds.
- `GET /v1/evolution/evidence/kinds/{kind}` — list evidence items for one kind.
- `GET /v1/evolution/evidence/nav/proposals/{proposal_id}` — navigate linked evidence for one proposal.

## Evidence kinds

- inspections
- plans
- proposals
- guards
- baselines
- actions
- schedules
- dashboards

## Navigation model

Proposal navigation resolves the most important linked objects:

- proposal
- inspection
- plan
- guard
- baseline
- actions
- dashboard artifacts

This is intended for reviewer/operator traceability and evidence lookup.
