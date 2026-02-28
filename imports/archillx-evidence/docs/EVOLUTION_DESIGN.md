# Evolution Module (v45)

This document describes the first operational slice of Archillx self-improvement.

## Included in v45
- signal collection from telemetry/readiness/migration/audit/gate evidence
- inspection report generation
- issue classification
- prioritized evolution plan generation
- evidence persistence under `evidence/evolution/`
- API endpoints:
  - `GET /v1/evolution/status
/v1/evolution/summary
`
  - `GET /v1/evolution/report`
  - `POST /v1/evolution/report/run`
  - `GET /v1/evolution/plan`
  - `POST /v1/evolution/plan/run`

## Not yet included
- patch proposal generation
- guard pipeline for proposals
- baseline comparison for upgrades
- auto-apply / approval workflow

## Evidence layout
- `evidence/evolution/inspections/*.json`
- `evidence/evolution/plans/*.json`


## Proposal engine (v46)

The v46 baseline adds a first patch proposal engine. It generates proposal evidence from the latest evolution plan, assigns a simple risk score, suggests affected files/tests, and records rollout notes. This is still proposal-only: no automatic patch application is performed.


## Evolution upgrade guard (v47)

This release adds an upgrade guard stage for evolution proposals, including compileall, pytest, smoke, release gate, rollback gate, and migration checks.


## Baseline Compare (v48)

The evolution subsystem can now compare the latest inspection snapshot against the current runtime signals, producing a baseline comparison report with regression detection.


## v50 auto proposal scheduling

- `ENABLE_EVOLUTION_AUTO=true` enables scheduled evolution cycles.
- `EVOLUTION_AUTO_CYCLE_CRON` controls the cycle schedule.
- `POST /v1/evolution/schedule/run` triggers one full automatic cycle.
- Low-risk proposals can automatically enter guard when `EVOLUTION_AUTO_GUARD_LOW_RISK=true`.


- v51 evolution additions: `/v1/evolution/proposals/list`, `/v1/evolution/proposals/{proposal_id}` for proposal listing/filtering by status, risk level, and subject.


- Evolution actions filtering API: `/v1/evolution/actions/list` supports `action`, `actor`, `proposal_id`, `from_status`, `to_status`.


## Governance guide (v54)

For approval roles, proposal state transitions, operator checklists, and governance boundaries, see `docs/EVOLUTION_GOVERNANCE.md`.


## v55 Evolution dashboard summary

- API: `POST /v1/evolution/dashboard/render`
- Evidence output: `evidence/evolution/dashboards/evolution_summary_*.{json,md,html}`


## Auto-approve policy (v56)

The auto scheduler may move a proposal from `generated` or `guard_passed` to `approved` when the proposal is low-risk, `auto_apply_allowed=true`, `approval_required=false`, and the configured guard requirement is satisfied.


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


## v70 additions

- `/ui` management console skeleton
- proposal patch artifact bundle (`patch.diff`, `pr_draft.md`, `tests_to_add.md`, `rollout_notes.md`, `risk_assessment.json`)


## v73 patch artifact templates

Patch artifacts now also include `pr_title.txt` and `commit_message.txt` templates alongside `patch.diff`, `pr_draft.md`, `tests_to_add.md`, and `rollout_notes.md`.
