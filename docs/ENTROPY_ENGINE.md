# Entropy Engine v1.0

ArcHillx 引入系统级稳定性模块 **Entropy Engine v1.0**，用于持续量化无序度、预测失稳趋势并给出负熵动作建议。

## Placement

`OODA Loop -> Governor -> Entropy Engine -> Stabilization Actions`

## Components

1. **Entropy Collector**: memory/task/model/resource/decision 五维采样。
2. **Entropy Calculator**: 静态权重评分（默认每维 0.20）。
3. **Instability Predictor**: EWMA + volatility + forecast window。
4. **Negentropy Actuator**: 规则化修复建议（Memory Compaction / Task Rebalancing / Router Reset / Circuit Mode Shift / Goal Re-alignment）。

## State machine

`NORMAL -> WARN -> DEGRADED -> CRITICAL -> RECOVERY -> NORMAL`

每次 `tick` 会输出审计记录到 `evidence/entropy_engine.jsonl`。

## Audit schema

```json
{
  "timestamp": "...",
  "entropy_score": 0.42,
  "entropy_vector": {
    "memory": 0.33,
    "task": 0.55,
    "model": 0.41,
    "resource": 0.28,
    "decision": 0.52
  },
  "risk_level": "WARN",
  "triggered_action": ["Task Rebalancing"],
  "recovery_time": null,
  "governor_override": false
}
```

## API

- `GET /v1/entropy/status`: 返回当前快照（不写证据）。
- `POST /v1/entropy/tick`: 计算并落盘证据。
- `GET /v1/system/monitor`: 监控 UI 聚合输出中包含 `entropy` 字段。

## Thresholds

- `< 0.3` -> `NORMAL`
- `0.3 - 0.5` -> `WARN`
- `0.5 - 0.7` -> `DEGRADED`
- `> 0.7` -> `CRITICAL`


## Gate (P0)

上线前必须通过：

- `/v1/entropy/status` 包含 `score/vector/risk/state/ts`
- `/v1/entropy/tick` 触发后 `evidence/entropy_engine.jsonl` 新增记录
- `/v1/system/monitor` 的 `entropy` 与 `/v1/entropy/status` 一致（时间差 < 2s）
- 状态机转移会写 `event=state_transition` 审计
- UI fail-soft：Monitor 页即使 entropy 渲染异常也不影响整页

一键验证：

```bash
python scripts/verify_entropy_engine.py
```

会输出 `OK_*` 结果并生成：

- `evidence/reports/ENTROPY_VERIFY_<YYYYMMDD_HHMMSS>.json`
- 报告内含 `entropy_engine.jsonl` 的 `sha256`


## Contract vs Non-contract Fields

### Stable contract (API compatibility required)

- `score`
- `vector`
- `risk`
- `state`
- `ts`

这些字段是外部调用与监控聚合的稳定契约，后续版本不得随意删除或改名。

### Non-contract (can evolve)

- `predictor` 细节结构
- `triggered_action` 语义扩展
- `version`
- 其他辅助调试字段（如 `entropy_*` 别名字段）

## Monitor consistency semantics

- `/v1/entropy/status` 返回当前缓存快照（若首次调用会初始化一次计算）。
- `/v1/entropy/tick` 才是推进状态机并写入审计 evidence 的入口。
- `/v1/system/monitor` 读取的是 `status()` 缓存快照，不做强制重算。

因此 monitor 的 entropy 是“近实时快照”，不是“每次请求都重算”。
