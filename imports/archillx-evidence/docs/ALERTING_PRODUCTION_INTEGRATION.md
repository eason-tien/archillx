# Archillx Alerting Production Compose Integration

This note explains how to attach the Prometheus / Alertmanager starter assets to the main production compose stack.

## Recommended pattern

Keep the base application stack in `docker-compose.prod.yml` and layer alerting with:

- `deploy/prometheus/docker-compose.alerting.example.yml`
- `docker-compose.prod.override.yml` (or a dedicated alerting override)

This keeps the core application stack small while allowing alerting to be enabled only in environments that need it.

## Compose invocation examples

### Base production stack only

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

### Production stack + alerting starter

```bash
docker compose --env-file .env.prod \
  -f docker-compose.prod.yml \
  -f deploy/prometheus/docker-compose.alerting.example.yml \
  up -d
```

### Production stack + local override + alerting

```bash
docker compose --env-file .env.prod \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.override.yml \
  -f deploy/prometheus/docker-compose.alerting.example.yml \
  up -d
```

## Main integration points

### Prometheus target

The starter configuration scrapes:

- `archillx:8000`
- `metrics_path: /v1/metrics`

This assumes the `archillx` service remains on the shared compose network.

### Alertmanager config

Start from:

- `deploy/alertmanager/alertmanager.example.yml`

Before production rollout, replace example webhook targets with real endpoints.

### Networks

The starter alerting compose file expects:

- `backend`
- `edge`

If you rename networks in production, update both:

- `docker-compose.prod.yml`
- `deploy/prometheus/docker-compose.alerting.example.yml`

## Volumes and retention

The starter file defines:

- `prometheus_data`
- `alertmanager_data`

For longer retention or external storage, replace named volumes with bind mounts or platform storage classes.

## Rollout order

1. Bring up the base production stack.
2. Verify `/v1/ready` and `/v1/metrics`.
3. Add the alerting compose layer.
4. Open Prometheus and confirm target health.
5. Open Alertmanager and verify active configuration.
6. Review `docs/ALERTING.md` and `docs/OPERATIONS_RUNBOOK.md` for response routing.

## Validation checklist

- `archillx` target is UP in Prometheus
- `/v1/metrics` is reachable from Prometheus
- Alertmanager receivers point to real endpoints
- `alert_domain` labels match expected runbook owners
- release / rollback / recovery alerts are routed to the correct responders

## Recommended related docs

- `docs/ALERTING.md`
- `docs/METRICS_DASHBOARD.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/RELEASE_ROLLBACK_RESTORE_RUNBOOK.md`

## Receiver ownership and response routing

Before rollout, align each `alert_domain` with the recommended owner mapping in:

- `docs/ALERTING_RECEIVERS_AND_OWNERS.md
- webhook receiver payload flow now documented in the owner mapping guide`


- `docs/ALERT_WEBHOOK_CONSUMER_TEMPLATE.md`


- `deploy/alertmanager/examples/fastapi_consumer.py`
- `deploy/alertmanager/examples/flask_consumer.py`


- `deploy/alertmanager/examples/common_payload.py`


- Alert webhook consumer test examples:
  - `deploy/alertmanager/examples/test_fastapi_consumer_example.py`
  - `deploy/alertmanager/examples/test_flask_consumer_example.py`
