# ArcHillx metrics and dashboard guide

This guide maps the runtime metrics exposed by `/metrics` and `/v1/telemetry` to practical dashboard panels and alert ideas.

## Endpoints

- `/metrics` and `/v1/metrics`: Prometheus style plaintext metrics.
- `/v1/telemetry`: JSON snapshot of counters, gauges, and timer aggregates.
- `/v1/telemetry` now exposes three layers: `snapshot`, `aggregate`, and `history`.
- `/v1/live` and `/v1/ready`: liveness and readiness probes.

## Metric groups

### HTTP and platform

Use these for traffic and platform health:

- `archillx_http_requests_total`
- `archillx_http_status_2xx_total`
- `archillx_http_status_4xx_total`
- `archillx_http_status_5xx_total`
- `archillx_http_request_seconds_sum`
- `archillx_http_request_seconds_count`
- `archillx_http_request_seconds_avg`
- `archillx_auth_failed_total`
- `archillx_rate_limited_total`
- `archillx_uptime_seconds`

Recommended panels:

1. Request rate
2. Error rate (4xx/5xx)
3. Average request latency
4. Authentication failures
5. Rate limit hits
6. Process uptime

Recommended alerts:

- `5xx > 0 for 5m`
- `rate_limited_total` rising faster than normal baseline
- readiness degraded while request rate is non-zero

### Governor

Use these to understand policy pressure and risk posture:

- `archillx_governor_evaluations_total`
- `archillx_governor_decision_approved_total`
- `archillx_governor_decision_warned_total`
- `archillx_governor_decision_blocked_total`
- `archillx_governor_last_risk_score`

Recommended panels:

1. Governor decisions stacked by outcome
2. Latest risk score gauge
3. Blocked decision trend

Recommended alerts:

- blocked decisions increase sharply over 10m
- last risk score remains above threshold for repeated runs

### Skills

Use these to understand tool health and user-facing execution quality:

- `archillx_skill_invoke_total`
- `archillx_skill_invoke_success_total`
- `archillx_skill_invoke_failure_total`
- `archillx_skill_validation_error_total`
- `archillx_skill_access_denied_total`
- `archillx_skill_disabled_total`

Per-skill metrics are emitted with normalized names, for example:

- `archillx_skill_web_search_invoke_total`
- `archillx_skill_web_search_success_total`
- `archillx_skill_file_ops_access_denied_total`
- `archillx_skill_code_exec_failure_total`

Recommended panels:

1. Skill invoke volume by skill
2. Skill failure trend by skill
3. ACL deny trend for high-risk skills
4. Validation error trend

Recommended alerts:

- `code_exec` failures spike after deploy
- `file_ops` access denied spikes unexpectedly
- any critical skill has zero traffic when traffic is expected

### Cron

Use these to understand scheduled automation reliability:

- `archillx_cron_execute_total`
- `archillx_cron_success_total`
- `archillx_cron_failure_total`
- `archillx_cron_blocked_total`

Per-job metrics are emitted with normalized names, for example:

- `archillx_cron_job_daily_sync_execute_total`
- `archillx_cron_job_daily_sync_success_total`
- `archillx_cron_job_daily_sync_failure_total`
- `archillx_cron_job_daily_sync_blocked_total`

Recommended panels:

1. Cron success vs failure
2. Cron blocked count
3. Per-job execution heatmap or top failures

Recommended alerts:

- any important job has failures for 2 consecutive runs
- blocked cron jobs increase above expected baseline

### Sandbox and code execution

Use these for high-risk execution visibility:

- `archillx_sandbox_events_total`
- `archillx_sandbox_sandbox_preflight_total`
- `archillx_sandbox_sandbox_execute_start_total`
- `archillx_sandbox_sandbox_execute_done_total`
- `archillx_sandbox_sandbox_execute_failed_total`
- `archillx_sandbox_sandbox_denied_total`
- `archillx_sandbox_backend_process_total`
- `archillx_sandbox_backend_docker_total`
- `archillx_sandbox_decision_APPROVED_total`
- `archillx_sandbox_decision_WARNED_total`
- `archillx_sandbox_decision_BLOCKED_total`

Recommended panels:

1. Sandbox events by type
2. Sandbox backend split (process vs docker)
3. Sandbox decisions by outcome
4. Execution failure trend

Recommended alerts:

- sandbox denied spikes unexpectedly
- docker backend usage drops to zero when it should be active
- sandbox execute failed rises after release

## Minimal dashboard layout

### Row 1: service health
- uptime
- request rate
- latency
- error rate
- readiness state

### Row 2: control plane
- governor decisions
- latest risk score
- rate limit hits
- auth failures

### Row 3: execution plane
- skill invoke volume
- skill failures
- cron success/failure
- cron blocked

### Row 4: high-risk execution
- sandbox events
- sandbox decision split
- backend split
- `code_exec` success/failure


## Telemetry response structure

`/v1/telemetry` is no longer just a raw dump. The response is designed in three layers:

### `snapshot`
Raw counters, gauges, and timer summaries. Use this layer when you want exact cumulative values or need parity with `/metrics`.

### `aggregate`
Module-oriented summaries derived from the raw counters. This is the best layer for internal status pages and lightweight API consumers.

### `history`
Rolling-window summaries computed from recent in-memory events and timers. Current windows are:

- `last_60s`
- `last_300s`
- `last_3600s`

Each window includes grouped summaries for:

- `http`
- `governor`
- `skills`
- `cron`
- `sandbox`

The `history` section also reports retention information:

- `max_events`
- `max_timers`

## History windows: how to use them

Use history windows when cumulative counters are too blunt to answer "what is happening right now?".

### `last_60s`
Best for:

- deployment smoke validation
- rate-limit spikes
- sudden sandbox failures
- fast-moving incident triage

### `last_300s`
Best for:

- short operational trends
- cron instability during the last few runs
- governor block surges after a config change

### `last_3600s`
Best for:

- release-hour comparisons
- prolonged degradation analysis
- validating whether a fix actually improved behavior over the last hour

## Example telemetry interpretation

Suggested first checks during an incident:

1. `history.windows.last_60s.http.status.5xx`
2. `history.windows.last_60s.sandbox.blocked_total`
3. `history.windows.last_300s.skills.failure_total`
4. `history.windows.last_300s.cron.failure_total`
5. `aggregate.governor.decisions.blocked`
6. `snapshot.counters.archillx_auth_failed_total`

If `snapshot` is stable but `history.last_60s` spikes, the issue is recent and active.
If `history.last_60s` is calm but `history.last_3600s` is elevated, the system may be recovering from an earlier incident.

## Dashboard mapping for telemetry JSON

When you are not using Prometheus yet, map `/v1/telemetry` to panels like this:

- **Recent request pressure** → `history.windows.last_60s.http.requests_total`
- **Recent 5xx** → `history.windows.last_60s.http.status.5xx`
- **Recent rate limiting** → `history.windows.last_60s.http.rate_limited_total`
- **Governor pressure (5m)** → `history.windows.last_300s.governor.blocked_total`
- **Skill failures (5m)** → `history.windows.last_300s.skills.failure_total`
- **Cron failures (1h)** → `history.windows.last_3600s.cron.failure_total`
- **Sandbox policy blocks (5m)** → `history.windows.last_300s.sandbox.blocked_total`
- **Current overall counters** → `aggregate.*` or `snapshot.*`

## History-aware alert suggestions

When building alerts from telemetry rather than Prometheus, prefer windows over cumulative totals.

Examples:

- `history.windows.last_60s.http.status.5xx > 0`
- `history.windows.last_300s.skills.failure_total > baseline`
- `history.windows.last_300s.cron.failure_total > 0` for critical jobs
- `history.windows.last_60s.sandbox.blocked_total spikes unexpectedly`
- `history.windows.last_300s.governor.blocked_total rises immediately after a policy release`

## JSON telemetry usage

`/v1/telemetry` is useful when Prometheus is not yet deployed. Suggested uses:

- lightweight internal status page
- smoke checks after deploy
- debug snapshots during incident handling

Recommended fields to inspect first:

- `snapshot.counters`
- `aggregate.http`
- `aggregate.skills`
- `history.windows.last_60s`
- `history.windows.last_300s`

## Grafana example

A starter dashboard JSON is included at:

- `deploy/grafana/archillx-dashboard.json`

Import it into Grafana, then point Prometheus panels at the `archillx_*` metrics above.

## Alerting baseline

Start with these alerts before adding more:

1. readiness degraded for 5 minutes
2. HTTP 5xx count > 0 over 5 minutes
3. governor blocked decisions > baseline
4. cron failures on critical jobs
5. sandbox execute failed > baseline
6. auth failed or rate limited spikes

## Rollout guidance

When first deploying metrics dashboards:

1. collect a baseline for 3 to 7 days
2. set alerts based on observed baseline, not guesses
3. separate dashboards for platform, agent, and security views
4. review deny/block metrics after every release that changes ACL, governor, or sandbox logic


## v35 更细窗口

历史窗口中的 `skills.by_skill`、`cron.by_job`、`sandbox.by_backend` 与 `sandbox.by_decision` 可直接用于最近 60s / 300s / 3600s 的对象级观察。


## v36 panel refinement

The starter Grafana dashboard now uses rate/increase style expressions instead of raw cumulative counters for the most important panels. This makes the board more useful during live operations.

### New or refined panel groups

- **Request Rate (5m)**: `sum(rate(archillx_http_requests_total[5m]))`
- **HTTP 5xx Rate (5m)**: `sum(rate(archillx_http_status_5xx_total[5m]))`
- **Governor Blocked (5m)**: `sum(increase(archillx_governor_decision_blocked_total[5m]))`
- **Sandbox Failed (5m)**: `sum(increase(archillx_sandbox_sandbox_execute_failed_total[5m]))`
- **Auth Failed (5m)** and **Rate Limited (5m)** as control-plane safety indicators
- **Top Skill Invocations (15m)** using `archillx_skill_*_invoke_total` metrics
- **Top Cron Jobs (1h)** using `archillx_cron_job_*_execute_total` metrics
- **Sandbox Backend Split (1h)** to confirm `docker` vs `process` backend behavior

### Why these panels are better

Raw counters are still useful for troubleshooting, but panel views should usually answer **what is changing now**. Using `rate()` and `increase()` gives clearer answers for live dashboards and alerting.

### Suggested row layout after refinement

1. **Traffic & Errors**
   - Request Rate (5m)
   - HTTP 5xx Rate (5m)
   - HTTP Request Rate by Status
   - HTTP Latency Avg (5m)

2. **Control Plane**
   - Governor Blocked (5m)
   - Governor Decisions (5m)
   - Auth Failed (5m)
   - Rate Limited (5m)

3. **Execution Plane**
   - Skill Success vs Failure (5m)
   - Top Skill Invocations (15m)
   - Cron Success vs Failure (15m)
   - Top Cron Jobs (1h)

4. **High-risk Execution**
   - Sandbox Failed (5m)
   - Sandbox Decisions (15m)
   - Sandbox Backend Split (1h)

### Practical dashboard reading order

During an incident, read the board in this order:

1. Traffic and 5xx panels
2. Governor blocked and auth/rate-limit panels
3. Skill and cron failure panels
4. Sandbox failed / blocked / backend split panels

This order usually separates platform issues, policy issues, job issues, and high-risk execution issues quickly.


- `docs/ALERTING.md`
