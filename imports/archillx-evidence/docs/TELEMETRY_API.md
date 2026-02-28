# ArcHillx telemetry API guide

This guide describes the JSON structure returned by `GET /v1/telemetry`.

## Endpoint

- `GET /v1/telemetry`

The endpoint is intended for lightweight status pages, internal admin panels, smoke checks, and incident triage when Prometheus is not available or when a consumer prefers JSON.

## Response structure

Top-level fields:

- `service`
- `snapshot`
- `aggregate`
- `history`

## `snapshot`

Contains the raw in-memory telemetry store:

- `counters`
- `gauges`
- `timers`

Use `snapshot` for exact cumulative values and for parity with `/metrics`.

## `aggregate`

Contains grouped summaries derived from `snapshot`. Current groups include:

- `http`
- `governor`
- `skills`
- `cron`
- `sandbox`

This section is best for dashboards and API consumers that do not want to reconstruct metrics from raw counters.

## `history`

Contains rolling-window summaries computed from recent events and timer observations.

### Windows

- `last_60s`
- `last_300s`
- `last_3600s`

### Per-window groups

- `http`
- `governor`
- `skills`
- `cron`
- `sandbox`

### Retention fields

- `max_events`
- `max_timers`

## Example uses

### Post-deploy smoke check

Inspect:

- `history.windows.last_60s.http.status.5xx`
- `history.windows.last_60s.sandbox.blocked_total`
- `history.windows.last_60s.skills.failure_total`

### Control plane health

Inspect:

- `aggregate.governor.decisions.blocked`
- `aggregate.cron.totals.failure_total`
- `aggregate.skills.totals.access_denied_total`

### High-risk execution posture

Inspect:

- `aggregate.sandbox.backend`
- `aggregate.sandbox.decision`
- `history.windows.last_300s.sandbox.blocked_total`

## Compatibility guidance

- Use `snapshot` if you need raw values.
- Use `aggregate` if you are building cards, tables, or summaries.
- Use `history` if you need recent-behavior context.

## Related docs

- `docs/METRICS_DASHBOARD.md`
- `DEPLOYMENT.md`


## v35 更细窗口

历史窗口中的 `skills.by_skill`、`cron.by_job`、`sandbox.by_backend` 与 `sandbox.by_decision` 可直接用于最近 60s / 300s / 3600s 的对象级观察。


## Dashboard-focused notes (v36)

Even when Grafana is backed by Prometheus, the telemetry JSON is useful for internal status pages and lightweight operational UIs.

Recommended pairings:

- **Prometheus/Grafana** for rates, increases, and long-range charts
- **`/v1/telemetry`** for JSON summaries, recent window cards, and internal admin pages

Typical pairing examples:

- Grafana **Request Rate (5m)** panel ↔ `/v1/telemetry.aggregate.http.requests_total` plus `history.windows.last_60s.http.requests_total`
- Grafana **Top Skill Invocations (15m)** panel ↔ `/v1/telemetry.history.windows.last_300s.skills.by_skill`
- Grafana **Top Cron Jobs (1h)** panel ↔ `/v1/telemetry.history.windows.last_3600s.cron.by_job`
- Grafana **Sandbox Backend Split (1h)** panel ↔ `/v1/telemetry.history.windows.last_3600s.sandbox.by_backend`
