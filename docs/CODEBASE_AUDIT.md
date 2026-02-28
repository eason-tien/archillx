# ArcHillx 代码基线审计（当前仓库）

> 审计范围：`/workspace/archillx` 当前分支代码与本地可执行检查。
> 审计日期：自动化执行当次。

## 1. 总体结论

- **总体可运行**：核心包 `app/` 可被 Python 成功编译，V2 smoke test 通过。
- **架构完整**：项目覆盖 API 网关、OODA 主循环、技能系统、Governor、内存与定时任务。
- **主要风险集中在安全边界与测试基线**：存在潜在错误信息泄露点，以及测试依赖未完全安装导致全量 pytest 中断。

## 2. 关键模块盘点

- 入口应用：`app/main.py`（FastAPI 生命周期、认证、中间件、异常处理、路由挂载）。
- 技能执行：`app/skills/code_exec.py`（静态扫描 + sandbox worker + 审计事件上报）。
- 运行时：`app/runtime/*`（skill manager、cron）。
- 数据层：`app/db/schema.py` + SQLite / MySQL / MSSQL 可配置。
- 发布与运维文档齐全：README、DEPLOYMENT、RUNBOOK、METRICS 等。

## 3. 本次执行检查

1. `python -m compileall -q app`：通过。
2. `python scripts/smoke_test_v2.py`：通过（文件操作白名单拦截有效）。
3. `pytest -q`：失败，原因是示例集成测试依赖 `flask`，当前环境未安装该包。

## 4. 风险与改进建议

### A. 异常信息泄露（中优先级）

`app/main.py` 的全局异常处理将 `str(exc)` 原样返回给客户端。建议在生产模式下改为通用错误描述，仅在日志记录详细异常，避免内部信息暴露。

### B. 测试依赖不完整（中优先级）

`tests/test_alert_consumer_integration_examples.py` 依赖 `deploy/alertmanager/examples/flask_consumer.py`，后者需要 `flask`。建议：

- 将该测试标记为可选（如 `-m integration`），或
- 在 `requirements-dev.txt`/`requirements.txt` 明确补齐 Flask，或
- 在测试中按依赖可用性做 skip。

### C. 审计自动化建议（低优先级）

建议将 compileall、smoke test、pytest（按 unit/integration 分层）纳入 CI gate，减少发布前人工检查成本。

## 5. 结语

当前代码库具备较好的工程化基础，核心功能可运行。优先处理“异常信息返回策略”和“测试依赖分层”，可显著提升生产安全性与可维护性。


## 6. 闭环迭代结果（本轮）

- 已完成异常处理收敛：默认生产环境不再向客户端暴露 `reason=str(exc)`，仅在开发/测试环境或显式开启 `EXPOSE_INTERNAL_ERROR_DETAILS=true` 时返回详细原因。
- 已完成测试基线收敛：`tests/test_alert_consumer_integration_examples.py` 对 Flask 示例改为“依赖缺失则跳过 Flask 用例”，避免全量 pytest 因可选依赖中断。
- 闭环验证：`pytest -q` 全量通过（含 2 个 skip），`smoke_test_v2` 与 `compileall` 通过。
