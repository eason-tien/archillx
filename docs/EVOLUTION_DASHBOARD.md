# Evolution Dashboard Guide

This guide explains how to use the Evolution dashboard outputs that ArcHillx can generate from the self-evolution subsystem.

## Purpose

The Evolution dashboard is the operator-facing summary for the full evolution pipeline:

- inspection
- plan
- proposal
- guard
- baseline compare
- approval / reject / apply / rollback
- auto-scheduler

It is meant to answer three questions quickly:

1. **What is the current proposal pipeline state?**
2. **Which proposals are waiting for review or approval?**
3. **Are low-risk automation and guard/baseline steps behaving safely?**

## Data sources

The dashboard summary is derived from:

- `GET /v1/evolution/summary`
- `POST /v1/evolution/dashboard/render`
- proposal evidence in `evidence/evolution/proposals/`
- guard evidence in `evidence/evolution/guards/`
- baseline evidence in `evidence/evolution/baselines/`
- action evidence in `evidence/evolution/actions/`
- schedule evidence in `evidence/evolution/schedules/`

## API entry points

### Read current summary

- `GET /v1/evolution/summary`

Use this when you need the latest aggregated JSON view for dashboards or automation.

### Render dashboard bundle

- `POST /v1/evolution/dashboard/render`

Use this when you want frozen artifacts for review, handoff, or evidence retention.

The render endpoint writes three files:

- JSON summary
- Markdown summary
- HTML summary

## Summary structure

The summary payload contains these major sections:

### `counts`

High-level object counts across the evolution subsystem:

- inspections
- plans
- proposals
- guards
- baselines
- actions
- schedules

### `proposal_status`

Distribution of proposals by current state, such as:

- generated
- guard_passed
- guard_failed
- approved
- rejected
- applied
- rolled_back

### `proposal_risk`

Distribution of proposals by risk level:

- low
- medium
- high
- critical

### `proposal_subjects`

Hotspots by subject area, useful for spotting recurring trouble zones such as:

- sandbox
- migration
- auth
- acl
- code_exec
- file_ops

### `action_types`

Distribution of governance actions, for example:

- approve
- reject
- apply
- rollback

### `guard_status`

Pass/fail view over guard runs.

### `baseline_regressions`

Count of baseline comparisons that detected regression.

### `pipeline`

Operator-oriented health indicators:

- `pending_approval`
- `auto_apply_candidates`
- `actionable`
- `approved_or_applied`
- `guard_pass_rate`
- `regression_rate`

### `latest`

Latest object identifiers for quick drill-down:

- latest inspection id
- latest plan id
- latest proposal id
- latest guard id
- latest baseline id
- latest action id
- latest schedule id

### `schedule_overview`

Most recent scheduler cycle hints, including:

- latest cycle id
- generated proposal count
- generated limit

## Recommended dashboard cards

A practical dashboard should expose at least these cards:

### Row 1 — Pipeline overview

- Proposal count
- Pending approval
- Approved / applied
- Guard pass rate
- Regression rate

### Row 2 — Risk and review pressure

- Proposal risk distribution
- Proposal status distribution
- Top proposal subjects
- Action type distribution

### Row 3 — Automation safety

- Latest scheduler cycle id
- Latest scheduler proposal count
- Auto-guarded proposal share
- Baseline regression count

### Row 4 — Recent governance activity

- Latest proposal id
- Latest guard id
- Latest baseline id
- Latest action id

## Operator reading order

When the dashboard looks abnormal, use this order:

1. Check `pipeline.regression_rate`
2. Check `guard_status`
3. Check `proposal_risk`
4. Check `proposal_subjects`
5. Check `latest` ids and drill into the relevant evidence file

## Review workflow guidance

### Reviewer

Focus on:

- `proposal_risk`
- `proposal_subjects`
- `pipeline.pending_approval`
- the latest proposal and guard ids

### Approver

Focus on:

- `guard_pass_rate`
- `baseline_regressions`
- whether the proposal subject touches high-risk modules

### Operator

Focus on:

- `schedule_overview`
- `approved_or_applied`
- latest action ids
- rendered dashboard artifact paths

## Evidence retention

Rendered dashboard bundles are stored under:

- `evidence/evolution/dashboards/`

Recommended retention practice:

- keep daily JSON summaries
- keep Markdown/HTML summaries for release windows and incidents
- attach dashboard bundle paths to release or rollback evidence when relevant

## HTML dashboard refinement (v59)

The rendered HTML bundle is now structured as an operator-facing dashboard rather than a plain list dump.

It includes:

- a hero summary with latest ids and window size
- KPI cards for:
  - pending approval
  - actionable proposals
  - guard pass rate
  - regression rate
- dedicated panels for:
  - counts
  - pipeline summary
  - proposal status
  - proposal risk
  - subject hotspots
  - guard and baseline
  - governance activity
  - latest objects
  - scheduler overview
  - recommended operator actions

Use the HTML bundle during review windows, incident handling, or handoff meetings when JSON is too raw and Markdown is too compact.

## Suggested alert triggers

These conditions should trigger manual review:

- `pipeline.regression_rate > 0`
- `guard_pass_rate` drops sharply
- proposal count spikes in a high-risk subject
- repeated `guard_failed` or `rolled_back` outcomes
- scheduler keeps producing proposals but actions stay flat

## Cross-links

See also:

- `docs/EVOLUTION_DESIGN.md`
- `docs/EVOLUTION_GOVERNANCE.md`
- `docs/EVOLUTION_RUNBOOK.md`
- `docs/OPERATIONS_RUNBOOK.md`


- `docs/EVOLUTION_NAVIGATION.md`
