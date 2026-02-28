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
