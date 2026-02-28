# Archillx Alerting

This guide explains the starter alerting assets for Archillx.

## Included assets

- `deploy/prometheus/prometheus.yml`
- `deploy/prometheus/alert_rules.yml`
- `deploy/prometheus/docker-compose.alerting.example.yml`
- `deploy/alertmanager/alertmanager.example.yml`

## Purpose

These files provide a first-pass alerting stack for:

- platform / API health
- governor blocks
- sandbox failures
- release / rollback / recovery observability handoff

## How to use

1. Start from `docker-compose.prod.yml` for the main stack.
2. Merge or adapt `deploy/prometheus/docker-compose.alerting.example.yml` into your production compose set.
3. Adjust webhook receiver URLs in `deploy/alertmanager/alertmanager.example.yml`.
4. Tune thresholds in `deploy/prometheus/alert_rules.yml`.
5. Pair alert actions with `docs/OPERATIONS_RUNBOOK.md` and `docs/RELEASE_ROLLBACK_RESTORE_RUNBOOK.md`.

## Rollout guidance

- Start with warning-level notifications only.
- Observe false positives for 1-2 weeks.
- Promote stable rules to paging / critical routes.
- Keep release / rollback alerts tied to gate evidence review.

## Production compose integration

For the recommended `docker compose -f ...` layering pattern and rollout order, see:

- `docs/ALERTING_PRODUCTION_INTEGRATION.md`

## Receivers and owner mapping

For concrete receiver names and alert domain ownership guidance, see:

- `docs/ALERTING_RECEIVERS_AND_OWNERS.md
- webhook receiver payload flow now documented in the owner mapping guide`


- `docs/ALERT_WEBHOOK_CONSUMER_TEMPLATE.md`


- `deploy/alertmanager/examples/fastapi_consumer.py`
- `deploy/alertmanager/examples/flask_consumer.py`


- `deploy/alertmanager/examples/common_payload.py`


- Alert webhook consumer test examples:
  - `deploy/alertmanager/examples/test_fastapi_consumer_example.py`
  - `deploy/alertmanager/examples/test_flask_consumer_example.py`
