# Stage 39：Agent 自然语言 API Bridge

日期：2026-08-31  
状态：实现与自动化验收完成；真实限额复测待执行。

## 完成内容

- 新增 `POST /api/agent/run`，复用既有 `run_agent_conversation()`。
- 新增最小 Request Schema：`message`、`conversation_id`、`max_turns`、`idempotency_key`。
- 新增 Agent 结果持久化桥接：只有已成功写入数据库的 PubMed Lead 才会返回为 `current_turn_lead_ids`。
- 返回 `conversation_id`、`primary_task_id`、`task_ids_by_source`、本轮与历史 Lead ID、Tool、数据源、artifact 元数据和结果统计。
- 不向 API 返回本地绝对路径、模型配置、SMTP 信息或原始内部异常。
- 新增 Agent Run 幂等记录；同一 `idempotency_key` 的成功重试返回缓存结果，不重复执行 Agent 或创建业务记录。
- Vue “Agent 对话”页已从占位提示替换为真实 API 调用，并在浏览器会话中复用 `conversation_id`。
- 未新增 Agent 可调用的发送邮件、批量发送、审批或 SMTP Tool。

## 新增或修改的主要文件

- `src/scholarlead_agent/api/routers/agent.py`
- `src/scholarlead_agent/api/schemas/agent.py`
- `src/scholarlead_agent/services/agent_result_persistence.py`
- `src/scholarlead_agent/agent/loop.py`
- `src/scholarlead_agent/agent/tool_types.py`
- `src/scholarlead_agent/tools/pubmed_tool.py`
- `src/scholarlead_agent/database.py`
- `frontend/src/api.js`
- `frontend/src/App.vue`

## 验证结果

离线 Mock 测试：

```text
29 passed, 1 warning
```

前端构建：

```text
npm run build: passed
```

全量 Python 回归：

```text
396 passed, 1 warning
```

所有自动化测试均未访问真实模型、PubMed、SMTP 或其他真实网络服务。

真实小范围 smoke test：

```text
任务：请检索最多 3 篇 2025 年以来与 single-cell cancer 相关的 PubMed 论文，
      优先保留有公开验证邮箱的候选 PI。不要生成或发送邮件。
结果：Agent 调用 PubMed，成功持久化 3 篇论文和 8 条公开邮箱 Lead。
确认：Agent 返回了 PubMed 来源和公开邮箱证据；数据库中无新增邮件发送记录。
```

## 已知限制

- 当前持久化桥接第一版只对保留了内部运行对象的 PubMed Tool 执行既有数据库持久化；其他数据源会如实返回来源任务信息，但不被误标记为已创建数据库 Lead。
- Agent API 是同步接口；多数据源和多轮模型调用可能耗时较长，本阶段未引入异步 Worker 或实时进度。
- 同一请求在服务器异常中断后可用相同幂等键重新执行；跨进程并发与生产级分布式幂等治理不属于本阶段。
- 当前 Vue 客户列表默认仍可查看全部历史 Lead；通过本轮 Agent 结果中的“查看客户列表”进入时，会按 `current_turn_lead_ids` 过滤为本轮结果。

## 下一步

首次真实 smoke test 已验证 Agent、PubMed、持久化和 Vue 展示链路，但审计发现模型曾请求 `max_results=10`。现已在 Agent API 注入 `ToolContext(max_results_limit=5)`，由 ToolRegistry 在实际调用工具前通用收紧该参数；自动化测试已覆盖。完成一次新的真实小范围 smoke test，并确认实际 Tool 参数不超过 5 且未发送邮件后，Stage 39 才达到验收标准。
