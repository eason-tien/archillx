# System + Evolution Integration Delivery Guide

## Purpose

This document describes how the **core Archillx runtime** and the **evolution subsystem** fit together as one deliverable system.

It is intended for:
- platform owners
- operators
- approvers/reviewers
- deployment engineers
- handoff recipients

The goal is to make it clear **what belongs to the main system**, **what belongs to evolution**, and **how the two interact safely**.

---

## 1. Integration overview

Archillx now has two strongly-related layers:

### A. Core runtime layer
The main runtime is responsible for:
- API serving
- agent execution
- OODA loop
- skill execution
- cron scheduling
- governor decisions
- memory / goals / sessions / tasks
- sandboxed code execution
- audit logging
- readiness / migration / release / rollback gates
- deployment and operations assets

### B. Evolution subsystem layer
The evolution subsystem is responsible for:
- inspecting the current system state
- classifying issues
- generating prioritized evolution plans
- generating patch proposals
- running upgrade guard checks
- comparing before/after baselines
- governing approval / rejection / apply / rollback state
- auto-scheduling low-risk proposal flows
- rendering dashboard / portal / subsystem / final bundles
- indexing evidence and providing navigation across artifacts

### Relationship
The evolution subsystem does **not** replace the main runtime.
It sits **on top of** the main runtime and uses the main runtime's telemetry, audit, readiness, migration, release, rollback, and operational evidence as input signals.

---

## 2. Architectural boundary

### Core runtime owns
- execution of user/agent work
- security boundaries
- sandbox enforcement
- file/code execution restrictions
- API authentication
- cron orchestration
- persistence and migrations
- release / rollback / restore controls

### Evolution owns
- self-observation
- issue analysis
- proposal generation
- guard/baseline governance
- reviewer/operator visibility
- low-risk controlled automation
- evidence navigation and bundle rendering

### Critical rule
Evolution may **observe, summarize, propose, validate, and govern**.
It must **not bypass**:
- sandbox policy
- auth / ACL policy
- migration safety checks
- release gate
- rollback gate
- restore drill expectations

---

## 3. Data and signal dependencies

The evolution subsystem consumes signals from the main system.

### Primary signal sources
- `/v1/telemetry`
- `/v1/ready`
- `/v1/migration/state`
- `/v1/audit`
- `/v1/audit/summary`
- release check evidence
- rollback check evidence
- restore drill evidence
- gate summary evidence

### What evolution derives from those signals
- findings
- plans
- proposals
- guard runs
- baseline comparisons
- governance actions
- schedule cycles
- dashboard / navigation / portal / final bundles

---

## 4. API integration map

### Core system API groups
- `/v1/agent/*`
- `/v1/skills/*`
- `/v1/memory/*`
- `/v1/cron/*`
- `/v1/audit*`
- `/v1/metrics`
- `/v1/telemetry`
- `/v1/ready`
- `/v1/migration/state`

### Evolution API groups
- `/v1/evolution/status`
- `/v1/evolution/report`
- `/v1/evolution/plan`
- `/v1/evolution/proposals*`
- `/v1/evolution/guard`
- `/v1/evolution/baseline`
- `/v1/evolution/actions*`
- `/v1/evolution/schedule*`
- `/v1/evolution/summary`
- `/v1/evolution/dashboard/render`
- `/v1/evolution/evidence/*`
- `/v1/evolution/subsystem*`
- `/v1/evolution/nav*`
- `/v1/evolution/portal*`
- `/v1/evolution/final*`

### Reading order for operators
1. `/v1/ready`
2. `/v1/telemetry`
3. `/v1/audit/summary`
4. `/v1/evolution/summary`
5. `/v1/evolution/portal`
6. `/v1/evolution/final`

---

## 5. Deployment integration

### Runtime deployment prerequisites
- production env configured
- database reachable
- migration state at head
- sandbox image and hardening policy in place if code execution is enabled
- release gate passes
- rollback gate passes
- backup verification passes

### Evolution deployment prerequisites
- core runtime healthy
- telemetry enabled or available
- audit evidence directory writable
- evolution feature enabled
- evidence directories writable

### Recommended enablement order
1. Deploy core runtime first
2. Validate readiness, migration, telemetry, audit
3. Run release gate and rollback gate
4. Enable evolution APIs and evidence paths
5. Run manual evolution inspection/plan/proposal once
6. Enable auto scheduler only after governance review
7. Enable low-risk auto-approve/apply only after operating confidence exists

---

## 6. Governance integration

### Roles
#### Operator
- monitors overall health
- runs release / rollback / restore gates
- uses portal / dashboard / evidence index
- executes approved actions and operational checks

#### Reviewer
- reviews findings, plans, proposals, dashboard outputs
- checks evidence quality and risk reasoning
- recommends approve / reject decisions

#### Approver
- authorizes proposals when approval is required
- confirms rollout / apply / rollback decisions
- owns high-risk change acceptance

### Automatic behaviors that remain bounded
Evolution may automatically:
- inspect
- classify
- plan
- generate proposals
- run guard for low-risk proposals
- auto-approve low-risk proposals when policy allows
- auto-apply low-risk proposals only under stricter conditions

Evolution may **not** automatically bypass high-risk governance boundaries.

---

## 7. Evidence integration map

### Core runtime evidence
- `evidence/security_audit.jsonl`
- `evidence/releases/*.json`
- `evidence/reports/*`
- restore drill outputs
- gate summary outputs

### Evolution evidence
- `evidence/evolution/inspections/`
- `evidence/evolution/plans/`
- `evidence/evolution/proposals/`
- `evidence/evolution/guards/`
- `evidence/evolution/baselines/`
- `evidence/evolution/actions/`
- `evidence/evolution/schedules/`
- `evidence/evolution/dashboards/`

### Integration expectation
When reviewing a proposal, the operator should be able to navigate:
- proposal → originating inspection/plan
- proposal → guard
- proposal → baseline
- proposal → approval/apply/rollback action history
- proposal → dashboard / portal / final bundles

---

## 8. Day-2 operating model

### Daily
- check `/v1/ready`
- check `/v1/telemetry`
- review `/v1/evolution/summary`
- review high-risk proposals and failed guards

### Weekly
- review dashboard / portal / final bundle
- review pending approvals
- review regression signals
- review restore drill status
- review gate summary trends

### Before enabling automation escalation
Do not enable low-risk auto-approve or auto-apply unless:
- release gate is consistently healthy
- rollback gate is consistently healthy
- restore drill is passing
- evidence navigation is working
- reviewers are satisfied with proposal quality

---

## 9. Recommended handoff package

For a team handoff, include:
- `docs/EVOLUTION_DELIVERY.md`
- `docs/EVOLUTION_DELIVERY_MANIFEST.md`
- `docs/EVOLUTION_GOVERNANCE.md`
- `docs/EVOLUTION_RUNBOOK.md`
- `docs/EVOLUTION_DASHBOARD.md`
- `docs/EVOLUTION_EVIDENCE.md`
- `docs/EVOLUTION_PORTAL.md`
- `docs/EVOLUTION_FINAL.md`
- this document

---

## 10. Final integration statement

The main system and the evolution subsystem should be treated as **one integrated platform** with **two operational layers**:

- the core runtime executes and protects work
- the evolution subsystem inspects, proposes, validates, governs, and navigates improvements

This separation is what allows self-improvement **without surrendering operational control**.
