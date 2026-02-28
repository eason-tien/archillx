# Evolution Approval & Governance Guide (v54)

This document describes how Archillx proposals are reviewed, approved, applied, and rolled back.

## Scope
Covers the evolution governance flow introduced through v49-v53:
- inspection
- plan
- proposal
- guard
- baseline compare
- approve / reject / apply / rollback
- auto proposal scheduling
- summary / list / filtering APIs

## Governance roles
### Reviewer
- reads inspection / plan / proposal details
- checks risk score and rationale
- confirms affected scope and tests to add
- does not apply production changes directly unless also acting as approver/operator

### Approver
- decides whether a proposal is acceptable for progression
- verifies guard results and baseline compare outcome
- confirms whether manual approval is required
- can approve or reject with reason

### Operator
- executes apply / rollback actions in a controlled environment
- verifies release/rollback gates
- confirms evidence was written and archived
- performs post-apply / post-rollback validation

## Core state flow
Typical state progression:
1. `generated`
2. `guard_passed` or `guard_failed`
3. `approved` or `rejected`
4. `applied`
5. optional `rolled_back`

## Mandatory checkpoints
Before approval, review:
- proposal risk score / risk level
- `requires_human_review`
- guard results
- baseline comparison
- latest migration state
- latest release / rollback gate evidence when relevant

Before apply, verify:
- proposal status is `approved`
- latest guard is `passed`
- no critical regression detected in baseline compare
- rollback path exists
- restore drill is recent enough for the target environment

Before rollback, verify:
- proposal status is `applied`
- rollback reason is captured
- rollback gate is green or explicitly waived with evidence
- backup archive / restore path exists if data-bearing change is involved

## Approval policy
### Auto-progress allowed
Can be auto-guarded and considered lower-risk when all apply:
- low risk score
- `auto_apply_allowed=true`
- does not touch sandbox/auth/ACL/migration/deployment/release/rollback paths
- has explicit test suggestions

### Manual approval required
Always require human approval for proposals touching:
- sandbox
- `code_exec`
- `file_ops`
- auth / ACL
- migration
- deployment assets
- release / rollback checks
- audit core

## Recommended reviewer checklist
- confirm proposal title matches subject
- confirm suggested changes are scoped and understandable
- confirm tests to add are sensible
- confirm rollout notes exist
- inspect guard failures if any
- inspect baseline regression flags

## Recommended approver checklist
- confirm risk level is acceptable for target environment
- confirm proposal is not stale
- confirm latest action trail is complete
- record explicit approval reason

## Recommended operator checklist
- run or verify release gate
- run or verify rollback gate
- verify migration state
- verify readiness / telemetry / audit summary after apply
- archive evidence paths

## Useful APIs
### Overview
- `GET /v1/evolution/status`
- `GET /v1/evolution/summary`

### Reports and planning
- `GET /v1/evolution/report`
- `POST /v1/evolution/report/run`
- `GET /v1/evolution/plan`
- `POST /v1/evolution/plan/run`

### Proposals
- `GET /v1/evolution/proposals`
- `GET /v1/evolution/proposals/list`
- `GET /v1/evolution/proposals/{proposal_id}`
- `POST /v1/evolution/proposals/generate`

### Guard / baseline
- `GET /v1/evolution/guard`
- `POST /v1/evolution/proposals/{proposal_id}/guard/run`
- `GET /v1/evolution/baseline`
- `POST /v1/evolution/proposals/{proposal_id}/baseline/run`

### Actions
- `GET /v1/evolution/actions`
- `GET /v1/evolution/actions/list`
- `GET /v1/evolution/actions/{action_id}`
- `POST /v1/evolution/proposals/{proposal_id}/approve`
- `POST /v1/evolution/proposals/{proposal_id}/reject`
- `POST /v1/evolution/proposals/{proposal_id}/apply`
- `POST /v1/evolution/proposals/{proposal_id}/rollback`

### Scheduling
- `GET /v1/evolution/schedule`
- `POST /v1/evolution/schedule/run`

## Evidence paths
- `evidence/evolution/inspections/`
- `evidence/evolution/plans/`
- `evidence/evolution/proposals/`
- `evidence/evolution/guards/`
- `evidence/evolution/baselines/`
- `evidence/evolution/actions/`
- `evidence/evolution/schedules/`

## Suggested day-2 operating rhythm
### Daily
- inspect `GET /v1/evolution/summary`
- review new proposals
- check guard failures and regressions

### Weekly
- review stale `generated` proposals
- review repeated rejected proposals to refine heuristics
- compare proposal distribution by subject/risk

### Release window
- re-check release / rollback gates
- ensure evolution evidence for the applied proposal is archived with deployment evidence

## Operator note
Evolution is designed to assist change governance, not bypass it. High-risk proposals must remain human-approved even if generated automatically.


## Low-risk auto-approve (v56)

When `ENABLE_EVOLUTION_AUTO=true` and `EVOLUTION_AUTO_APPROVE_LOW_RISK=true`, the scheduler may auto-approve proposals that are low-risk, do not require human approval, and satisfy the configured guard requirement.


## Linked runbook (v57)

For the day-2 operator flow and end-to-end execution order, see `docs/EVOLUTION_RUNBOOK.md`.


## v58 Evolution dashboard docs

- Guide: `docs/EVOLUTION_DASHBOARD.md`
- Summary API: `GET /v1/evolution/summary`
- Render API: `POST /v1/evolution/dashboard/render`


## v60 Auto-apply policy

Low-risk proposals may be auto-applied only when auto-apply is enabled, the proposal is low-risk and auto-apply eligible, auto-approval has already occurred, guard has passed (unless explicitly relaxed), and baseline compare reports no regression (unless explicitly relaxed). High-risk proposals remain manual.


- `docs/EVOLUTION_NAVIGATION.md`

- Navigation endpoints: `/v1/evolution/nav`, `/v1/evolution/nav/render`
