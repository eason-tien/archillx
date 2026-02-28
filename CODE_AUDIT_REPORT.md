# ArcHillx 全量代码审核报告（修正版）

## 审核范围
- `app/` 全模块（API、技能、运行时、治理、集成、通知、记忆层）。
- 本轮重点：文件系统边界、代码执行隔离、API 输入模型状态安全。

## 已完成修复

### 1) `file_ops` 白名单边界全面收敛
**文件**：`app/skills/file_ops.py`

- 对所有操作统一执行白名单校验（含 `read/list/exists`）。
- 增加操作名白名单，未知操作直接拒绝。
- 增加读取大小限制（2MB）避免超大文件读取风险。
- `list` 增加返回上限（1000）与 `truncated` 标记，修复边界判断并降低目录爆量开销。
- 支持 `ARCHILLX_FILE_WHITELIST`，并兼容历史拼写 `ARCHELI_FILE_WHITELIST`。

### 2) `code_exec` 执行隔离与资源约束增强
**文件**：`app/skills/code_exec.py`

- 增加代码长度上限（20,000 字符）避免异常大输入。
- 增加超时上下界（1s~30s），防止无限放大 timeout。
- `timeout_s` 参数增加容错解析（非数字输入回退默认值），避免运行时异常。
- 子进程改为 `python -I`（隔离模式）执行，屏蔽用户 site 包影响。
- 使用临时工作目录执行并收敛环境变量，仅保留必要最小集合。
- 维持输出截断与违规关键词扫描，减少滥用面。

### 3) Pydantic 可变默认值风险清理
**文件**：`app/api/routes.py`、`app/integrations/openclaw/routes.py`

- 将请求/响应模型中的 `{}` 与 `[]` 默认值替换为 `Field(default_factory=...)`。
- 避免跨请求共享可变对象导致的数据污染。

## 结论
本轮已对前次审阅中的关键问题做“可落地的全面修正”，覆盖：
- 文件访问边界
- 代码执行隔离与资源限制
- API 模型默认值安全

建议后续继续推进：
- 将 `code_exec` 从“进程隔离”升级为“容器级隔离 + seccomp/cgroup”。
- 在生产环境强制 API Key 非空启动（hard-fail）。
