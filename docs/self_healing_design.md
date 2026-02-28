# ArcHillx 自我修复与恢复系统（进一步设计）

## 1. 设计目标

基于现有 ArcHillx 架构，补齐“故障接管 → 自动修复 → 主系统恢复回切 → 自愈系统退出”的完整闭环，满足以下业务目标：

1. 当主系统或主 Agent 失去连接/失去工作能力时，自愈系统可自动接管。
2. 接管后自动执行基础修复，持续验证主系统恢复状态。
3. 当主系统恢复且具备接手能力时，自动关闭自愈接管流程并完成控制权交还。
4. 支持终端/API 手动触发自愈流程（运维应急场景）。

---

## 2. 现状与缺口（基于当前代码）

当前已具备：
- 生命周期管理（Session/Task/Agent 状态）
- OODA 主循环
- Cron 调度恢复
- RemediationPlanner（生成修复计划）
- TierClassifier（风险分级）

当前缺口：
- 无“自愈控制器（Self-Healing Controller）”统一编排。
- 无“主系统健康探针 + 接管状态机 + 回切条件”闭环。
- 无“自愈执行与主 Agent 控制权互斥机制”。
- 无可观测的自愈事件模型与 API 控制面。

---

## 3. 总体架构设计

新增一个轻量编排模块：

- `app/autonomy/self_healing/controller.py`
- `app/autonomy/self_healing/state_machine.py`
- `app/autonomy/self_healing/health_probe.py`
- `app/autonomy/self_healing/executor.py`
- `app/autonomy/self_healing/models.py`
- `app/autonomy/self_healing/store.py`

### 3.1 角色划分

- **Primary Agent（主系统 Agent）**：默认执行业务。
- **Self-Healing Agent（自愈 Agent）**：仅在接管窗口中执行修复。
- **Controller（控制器）**：判定是否接管、推进修复、触发回切。

### 3.2 控制原则

- 单活控制：同一时刻仅允许 Primary 或 Self-Healing 执行“变更类动作”。
- 最小修复：先执行低风险/可回滚动作，再升级到中高风险。
- 证据闭环：每次动作记录“计划-执行-验证-结果”。
- 自动回切：满足恢复判定 N 次连续成功后回切。

---

## 4. 状态机设计

建议状态：

- `IDLE`：正常模式，无接管。
- `DEGRADED`：健康异常已发现，等待阈值确认。
- `TAKEOVER`：自愈系统获得控制权。
- `REPAIRING`：执行修复计划步骤。
- `VERIFYING`：执行恢复验证（探针 + 关键任务）。
- `HANDOFF_READY`：满足回切条件，待交还。
- `HANDOFF`：执行控制权交还。
- `COOLDOWN`：短暂观察期，防止抖动。
- `FAILED`：自愈失败，转人工。

### 4.1 关键迁移条件

- `IDLE -> DEGRADED`：连续 `probe_fail_count >= X`。
- `DEGRADED -> TAKEOVER`：故障持续超阈值或手动强制。
- `TAKEOVER -> REPAIRING`：接管锁拿到（分布式锁/DB 锁）。
- `REPAIRING -> VERIFYING`：修复步骤执行完成。
- `VERIFYING -> HANDOFF_READY`：连续 `probe_ok_count >= Y` 且关键任务通过。
- `HANDOFF_READY -> HANDOFF`：主 Agent 可用且负载正常。
- `HANDOFF -> COOLDOWN -> IDLE`：交还成功并稳定运行。
- 任意状态 -> `FAILED`：超过重试上限/出现不可恢复错误。

---

## 5. 健康探针设计（Health Probe）

探针建议分层：

1. **进程层**：`/healthz` 可达、响应时延、HTTP 状态。
2. **能力层**：`/v1/health` 返回内容完整（skills/cron/model router）。
3. **执行层**：轻量任务冒烟（例如 `_model_direct` 或 `web_search`）。
4. **数据层**：DB 连通 + 简单读写验证。

输出统一结构：

```json
{
  "healthy": false,
  "score": 42,
  "checks": {
    "http": "fail",
    "db": "ok",
    "agent_loop": "degraded"
  },
  "reason": "agent_loop_timeout"
}
```

---

## 6. 修复执行策略（Executor）

### 6.1 分级动作库

- **L1（低风险）**：重试、清理临时状态、重建轻量缓存、重新加载技能。
- **L2（中风险）**：重启子模块（cron、router、skill manager）、切换 fallback provider。
- **L3（高风险）**：进程重启、回滚配置、降级运行模式。

### 6.2 执行顺序

- 默认 L1 -> 验证 -> L2 -> 验证 -> L3 -> 验证。
- 每层最多 `N` 次，超限即进入 `FAILED`。

### 6.3 与现有组件对接

- 使用 `RemediationPlanner.create_plan()` 生成候选步骤。
- 使用 `TierClassifier` 决定自动执行范围（TIER_1/TIER_2 自动，TIER_3 需人工确认）。
- 每步执行前通过 Governor 审计并落库。

---

## 7. 控制权交还（Handoff）

满足以下全部条件时，进入回切：

1. 主系统探针连续成功 `Y` 次（如 3 次）。
2. 关键路径任务成功（至少 1 个业务任务 + 1 个技能调用）。
3. 无新严重告警（最近 `T` 秒）。

回切动作：

1. 解除接管锁，标记 Primary 为 `running`。
2. Self-Healing Agent 标记 `idle` 或 `terminated`。
3. 写入一条 `handoff_success` 事件，并启动 `COOLDOWN` 观察。
4. 观察期间再失败则回到 `TAKEOVER`（防抖重入）。

---

## 8. API 与终端触发设计

新增 API 前缀：`/v1/self-healing/*`

- `POST /v1/self-healing/start`：手动启动接管（支持 `force=true`）。
- `POST /v1/self-healing/stop`：手动停止（仅运维管理员）。
- `GET /v1/self-healing/status`：查看状态机、当前阶段、最近错误。
- `GET /v1/self-healing/events`：查询自愈事件流水。
- `POST /v1/self-healing/handoff`：手动执行交还（紧急回切）。

终端触发（建议）：

```bash
curl -X POST http://localhost:8000/v1/self-healing/start \
  -H "Content-Type: application/json" \
  -d '{"reason":"manual_ops","force":true}'
```

---

## 9. 数据模型建议

新增表（示意）：

1. `ah_self_heal_session`
   - `id`, `state`, `owner_agent`, `started_at`, `ended_at`, `trigger`, `reason`
2. `ah_self_heal_event`
   - `id`, `session_id`, `phase`, `action`, `result`, `detail_json`, `created_at`
3. `ah_self_heal_lock`
   - `lock_name`, `owner`, `expires_at`

用途：
- 审计追踪
- 故障复盘
- 多进程/多副本下接管互斥

---

## 10. 安全与治理

- 所有高风险修复动作必须走 Governor 审批。
- `start/stop/handoff` API 必须要求 admin token。
- 增加自愈速率限制：单位时间最大修复次数。
- 对外部依赖失败做熔断，避免“自愈风暴”。

---

## 11. 配置项建议（新增）

在 `Settings` 增加：

- `enable_self_healing: bool = False`
- `self_heal_probe_interval_s: int = 15`
- `self_heal_fail_threshold: int = 3`
- `self_heal_recover_threshold: int = 3`
- `self_heal_cooldown_s: int = 120`
- `self_heal_max_attempts_per_stage: int = 3`
- `self_heal_lock_ttl_s: int = 60`

---

## 12. 分阶段落地计划

### Phase 1（MVP）
- 实现状态机 + 手动触发 + 健康探针 + L1 修复动作。
- 接通 `/v1/self-healing/start|status|events`。

### Phase 2
- 接入 RemediationPlanner + TierClassifier 自动分级执行。
- 完整自动回切逻辑 + cooldown 防抖。

### Phase 3
- 分布式锁与多实例协同。
- 指标看板（成功率、MTTR、回切稳定性）。

---

## 13. 验收标准（对应你的三点要求）

1. **自动接管**：在主 Agent 故障注入后 `<= 60s` 进入 `TAKEOVER`。
2. **自动修复与回切**：修复后自动进入 `HANDOFF` 并恢复 Primary 执行。
3. **终端启动**：可通过 `POST /v1/self-healing/start` 强制启动接管。

---

## 14. 风险与边界

- 若主系统进程完全崩溃，进程内自愈无法运行：需外部 supervisor（systemd/k8s）兜底重启。
- 高风险修复动作可能引发二次故障：必须有 rollback 与人工介入开关。
- 多 worker 下需共享锁，避免双重接管。

