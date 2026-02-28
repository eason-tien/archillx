# Evolution Runbook

This runbook links the full Evolution pipeline into an operator-facing execution flow.

## Scope

Covers the end-to-end path:

1. inspection
2. plan
3. proposal generation
4. guard execution
5. baseline comparison
6. approve / reject
7. apply / rollback
8. auto-scheduler review
9. dashboard / evidence review

## Roles

### Reviewer
- Reviews findings, plan items, proposal scope, risks, and suggested tests.
- Confirms that the proposal still matches the observed issue.

### Approver
- Approves or rejects proposals after guard + baseline evidence review.
- Must explicitly review any high-risk subject.

### Operator
- Runs API or scripts, checks evidence, applies approved proposals, and handles rollback if needed.

## Daily operating flow

### 1. Check current evolution status
- `GET /v1/evolution/status`
- `GET /v1/evolution/summary`
- `POST /v1/evolution/dashboard/render`

Review:
- latest inspection / plan / proposal / guard / baseline / action / schedule
- pending approval count
- guard pass rate
- regression rate

### 2. Review latest findings
- `GET /v1/evolution/report`
- `GET /v1/evolution/plan`

Look for:
- readiness degradation
- migration drift
- sandbox blocked spikes
- skill failure spikes
- gate failures

### 3. Review proposals
- `GET /v1/evolution/proposals/list?status=generated`
- `GET /v1/evolution/proposals/list?status=guard_passed`
- `GET /v1/evolution/proposals/list?risk_level=high`

Review:
- subject
- suggested changes
- tests to add
- rollout notes
- risk factors

### 4. Run or verify guard
- `POST /v1/evolution/proposals/{proposal_id}/guard/run`
- `GET /v1/evolution/guard`

Guard should cover:
- compileall
- pytest
- smoke
- release_check
- rollback_check
- migration_check

### 5. Run baseline comparison
- `POST /v1/evolution/proposals/{proposal_id}/baseline/run`
- `GET /v1/evolution/baseline`

Confirm:
- regression_detected=false
- no new readiness regression
- no worsening gate / sandbox / skill failure indicators

### 6. Decide
#### Approve
- `POST /v1/evolution/proposals/{proposal_id}/approve`

#### Reject
- `POST /v1/evolution/proposals/{proposal_id}/reject`

Use reject when:
- baseline regresses
- proposal scope is unclear
- tests are incomplete
- issue is not reproducible

### 7. Apply or roll back
#### Apply
- `POST /v1/evolution/proposals/{proposal_id}/apply`

#### Roll back
- `POST /v1/evolution/proposals/{proposal_id}/rollback`

Before apply:
- confirm release gate still passes
- confirm rollback evidence path exists
- confirm backup archive availability

Before rollback:
- confirm rollback gate passes
- confirm restore drill confidence is acceptable

## Auto-scheduler review

### Check scheduler state
- `GET /v1/evolution/schedule`
- `POST /v1/evolution/schedule/run`

Review:
- generated proposal count
- auto-guard results
- auto-approval records
- latest cycle evidence

### Auto-approve boundaries
Low-risk auto-approve is only acceptable when:
- proposal risk is low
- `auto_apply_allowed=true`
- `approval_required=false`
- guard status is passed
- subject is not high-risk

High-risk subjects must remain manually reviewed.

## Escalation rules

Escalate to manual review when any of the following is true:
- subject touches sandbox / auth / ACL / migration / file_ops / code_exec
- guard failed
- regression_detected=true
- readiness is degraded
- migration state is behind / unknown
- rollback gate shows failure

## Evidence map

### API / state
- `/v1/evolution/status`
- `/v1/evolution/summary`
- `/v1/evolution/report`
- `/v1/evolution/plan`
- `/v1/evolution/proposals/list`
- `/v1/evolution/actions/list`

### Evidence files
- `evidence/evolution/inspections/`
- `evidence/evolution/plans/`
- `evidence/evolution/proposals/`
- `evidence/evolution/guards/`
- `evidence/evolution/baselines/`
- `evidence/evolution/actions/`
- `evidence/evolution/schedules/`
- `evidence/evolution/dashboards/`

## Weekly review checklist

1. render dashboard summary
2. review pending approval proposals
3. inspect top recurring subjects
4. inspect action actor distribution
5. inspect auto-approved proposals
6. review any rolled-back proposal
7. compare guard pass rate week-over-week
8. review regression rate week-over-week

## Recommended linked docs
- `docs/EVOLUTION_DESIGN.md`
- `docs/EVOLUTION_GOVERNANCE.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/RELEASE_ROLLBACK_RESTORE_RUNBOOK.md`
- `docs/GATE_SUMMARY_DASHBOARD.md`


## v58 Evolution dashboard docs

- Guide: `docs/EVOLUTION_DASHBOARD.md`
- Summary API: `GET /v1/evolution/summary`
- Render API: `POST /v1/evolution/dashboard/render`


## v60 Auto-apply policy

Low-risk proposals may be auto-applied only when auto-apply is enabled, the proposal is low-risk and auto-apply eligible, auto-approval has already occurred, guard has passed (unless explicitly relaxed), and baseline compare reports no regression (unless explicitly relaxed). High-risk proposals remain manual.


- `docs/EVOLUTION_EVIDENCE.md`


- `docs/EVOLUTION_SUBSYSTEM.md`


- `docs/EVOLUTION_NAVIGATION.md`

- Navigation endpoints: `/v1/evolution/nav`, `/v1/evolution/nav/render`


- `docs/EVOLUTION_PORTAL.md`
