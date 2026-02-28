# Entropy Alert Runbook v1.0

## Dedup semantics

- Dedup key: `sha256(state + risk + bucket_start + top_cause)`.
- 在 cooldown 窗口内同 dedup key 只发送一次。
- cooldown 到期后允许再次发送。

## WARN

### Trigger
- `risk=WARN` 且 `score >= entropy_threshold_normal`。

### Immediate checks
1. `GET /v1/entropy/status`
2. `GET /v1/entropy/trend?window=24h&bucket=1h`
3. `tail -n 50 evidence/entropy_engine.jsonl`

### Recommended handling
- 观察 trend 是否持续升高；
- 检查 backlog/fallback 波动；
- 暂不执行修复，仅记录处理意见。

### Clear condition
- 连续 tick 回到 `NORMAL`。

## DEGRADED

### Trigger
- `risk=DEGRADED` 且 trend 持续偏高。

### Immediate checks
1. `GET /v1/entropy/kpi?window=24h`
2. `GET /v1/entropy/proposals?status=PENDING`
3. `GET /v1/system/monitor`

### Recommended handling
- 由值班人员审核 proposal；
- 必要时执行低风险优化（task rebalance / router tighten）；
- 保持 governor 手动批准策略。

### Clear condition
- 状态进入 `RECOVERY` 或恢复到 `WARN/NORMAL`。

## CRITICAL

### Trigger
- `risk=CRITICAL` 或连续 `DEGRADED` 超阈值。

### Immediate checks
1. `GET /v1/entropy/status`
2. `GET /v1/entropy/proposals?status=PENDING`
3. `GET /v1/system/monitor` + recovery lock 状态

### Recommended handling
- 必须走治理流：proposal -> approve -> execute；
- 执行前确认 takeover lock 可获取；
- 执行后核对 evidence 与 KPI 回落。

### Clear condition
- 状态达到 `RECOVERY` 后回到 `NORMAL` 且 2 次 tick 稳定。
