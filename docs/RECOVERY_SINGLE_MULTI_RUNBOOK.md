# Recovery Controller Runbook (Single + Multi)

## Goals

- Automatic takeover when primary loses readiness/heartbeat.
- Repair and handoff back to primary after readiness recovers.
- Manual terminal rescue mode.

## Modes

- Single node (default): `RECOVERY_LOCK_BACKEND=file`
- Multi node: `RECOVERY_LOCK_BACKEND=redis` + `REDIS_URL=...`

## Key envs

- `RECOVERY_ENABLED=true`
- `RECOVERY_READY_URL=http://127.0.0.1:8000/readyz`
- `RECOVERY_HEARTBEAT_TTL_S=90`
- `RECOVERY_CHECK_INTERVAL_S=5`
- `RECOVERY_LOCK_TTL_S=30`

## Manual rescue

```bash
bash scripts/recovery/run_recovery.sh .env --once --force
```

Offline repair:

```bash
bash scripts/recovery/run_recovery.sh .env --once --force --offline
```

## Acceptance checks

1. Kill primary and ensure recovery acquires lock.
2. Verify evidence written to `evidence/recovery/recovery.jsonl`.
3. Verify handoff file appears in temp dir (`archillx_handoff.json`).
4. Ensure `/readyz` returns healthy after repair.
