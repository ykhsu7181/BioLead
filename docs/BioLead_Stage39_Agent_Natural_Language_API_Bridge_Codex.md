# BioLead Stage 39：Agent 自然语言 API Bridge

## 1. 目标与当前基线

本方案适用于 ScholarLead Agent；BioLead 是规划和产品名称。

当前已有：

- 有边界的 Agent Loop 与 `ToolRegistry`。
- 带 SQLite 对话持久化的 `run_agent_conversation()`。
- PubMed、OpenAlex、Crossref、NIH RePORTER 和邮件草稿 Agent Tool。
- FastAPI、Vue、客户详情、结果包和受控邮件发送流程。
- Vue 已有“Agent 对话”页面，但“运行 Agent”仍是占位提示，尚未调用真实 Runtime。

Stage 39 只打通以下最小闭环，不替换已有 Agent、数据源或邮件子系统：

```text
用户自然语言
-> POST /api/agent/run
-> run_agent_conversation()
-> ToolRegistry
-> 现有科研数据 Tool
-> Agent 结果持久化桥接
-> SQLite 中可支持的 task / paper / lead / evidence
-> 结构化 API 响应
-> Vue Agent 页面展示并进入现有客户列表
```

## 2. 范围

### 2.1 本阶段必须完成

1. 新增正式的 FastAPI Agent 执行接口。
2. 复用 `run_agent_conversation()`，不实现第二套 Agent Loop。
3. 返回前端可直接使用的结构化结果。
4. 通过已有 Runtime 持久化对话消息和 TaskContext。
5. 为有既有持久化能力的 Tool 结果增加独立结果持久化桥接。
6. 将 Vue 现有 Agent 占位入口替换为真实接口调用，保持最小改动。
7. 保持邮件发送不在 Agent Tool Registry 中。
8. 增加 Mock 单元测试、API 测试和前端最小测试，并运行全量回归。
9. Mock 全部通过后，进行一次明确、有限的真实小范围验证。

### 2.2 本阶段明确不做

- Redis、Celery、RQ、Dramatiq、独立 Worker。
- SSE、WebSocket、实时进度流、Dashboard 重构。
- 登录、权限、团队协作、生产部署。
- 新科研数据源。
- 重写 Agent Loop、ToolRegistry、PubMed Service 或数据库主结构。
- Agent 可调用的 `send_email`、`batch_send`、`real_recipient_send`、SMTP Tool。
- Vue Router、页面架构或视觉设计的大规模重构。

## 3. 对原方案的必要修订

### 3.1 结果持久化是必做桥接，不是默认已具备

现有 Agent PubMed Tool 会生成运行结果并保存 raw/processed 文件，但不会像 `/api/pubmed/search` 一样调用既有 `persist_pubmed_run_result()` 写入数据库。

因此，只新增 Agent Router 并不能保证返回的 Lead 能继续通过 `GET /api/leads/{lead_id}` 查询。

实现边界：

```text
Agent Router
-> Agent Runtime
-> Agent Result Persistence Bridge
-> 既有的 source-specific persistence helper
```

Router 中不得写直接 SQL、直接 PubMed 调用或来源特定解析逻辑。

建议新增：

```text
src/scholarlead_agent/services/agent_result_persistence.py
```

该服务仅从结构化 Tool 结果中提取可持久化数据，并委托既有持久化函数；不得从 `final_answer` 用正则猜测 Lead ID。

对于尚无稳定数据库持久化路径的数据源，应保留其 raw/processed 输出并如实返回来源结果，但不得声称它已创建数据库 Lead。

持久化顺序必须明确：

```text
Tool 成功
-> 结果持久化成功
-> 返回 persisted Lead ID
```

只有已成功写入数据库、并可由既有 Lead API 查询的 Lead，才可计入 `current_turn_lead_ids` 和 `persisted_lead_count`。如果 Tool 成功但持久化失败，接口返回 `AGENT_RESULT_PERSISTENCE_FAILED`；不得将未入库 Lead 表示为可用结果。已保存的 raw/processed 文件不因持久化失败而删除。

### 3.1.1 持久化幂等性

同一次用户操作发生网络重试、浏览器重复提交或 API 重试时，不得重复创建 task、paper、lead、evidence 或邮件草稿记录。

Request 可选接受 `idempotency_key`。前端在一次“运行 Agent”操作开始时生成该值；重试同一次操作时必须复用。持久化桥接以该 key 和来源任务标识识别已完成的写入，并返回已有的持久化结果。

幂等性只用于同一次操作的重试；不得因为论文标题、作者姓名或查询文本相同，就把不同时期的正常检索强行合并为同一个任务。

### 3.2 区分本轮结果与历史上下文

当前 `TaskContext.last_lead_ids` 是累计历史结果，适合用于后续对话，但不能直接表示“本轮新产生的 Lead”。

API 必须区分：

- `current_turn_lead_ids`：只从当前 `AgentRunResult.messages` 提取。
- `context_lead_ids`：可选返回的当前累计上下文 Lead ID。

不得从自然语言 `final_answer` 推断 ID。

### 3.3 明确多数据源 task 语义

一轮 Agent 可能调用多个数据源，一个含义不清的 `task_id` 容易误导。

响应采用：

- `primary_task_id`：有持久化主发现任务时返回，第一版通常是 PubMed task。
- `task_ids_by_source`：按来源记录可用的 task/run ID。

若没有创建可持久化主任务，`primary_task_id` 必须为 `null`，不得人为生成假 ID。

### 3.4 不返回本地绝对文件路径

现有 Tool 数据可能包含本地 `run_report_path`。API 不得将 `D:\...` 这类绝对路径返回给前端。

改为返回受控 artifact 元数据：

```json
{
  "artifacts": [
    {"source": "pubmed", "kind": "run_report", "name": "pubmed_run_report_...json"}
  ]
}
```

以后如需下载，再通过单独受控接口实现；本阶段不开放任意本地文件访问。

### 3.5 Vue 需要完成最小真实接入

项目已有对用户可见的“Agent 对话”入口，因此 Stage 39 必须将其从占位功能改为真实调用，而不是只完成后端接口。

最小 UI 要求：

1. 在 `frontend/src/api.js` 增加 `runAgent()`。
2. 调用 `POST /api/agent/run`。
3. 在浏览器会话中保留返回的 `conversation_id` 用于追问。
4. 展示 `final_answer`、状态、调用 Tool、数据源和本轮 Lead 数量。
5. 有 Lead 时可刷新或进入已有客户列表。

不做流式对话、复杂聊天历史、设置页或页面重构。

## 4. API 设计

### 4.1 Endpoint

```http
POST /api/agent/run
```

### 4.2 Request

```json
{
  "message": "寻找美国近一年从事单细胞肿瘤研究、且优先有公开邮箱的 PI。",
  "conversation_id": null,
  "max_turns": 6,
  "idempotency_key": "agent-run-..."
}
```

校验规则：

- `message`：去除首尾空格后必填，最大 2,000 字符。
- `conversation_id`：可选、非空的不透明字符串。
- `max_turns`：可选整数，范围 `1-6`，默认 `6`。
- `idempotency_key`：可选、非空的不透明字符串；同一次操作重试时必须复用。
- 接口不接收任意 Tool 名称、原始 Tool 参数、模型配置、数据库路径、SMTP 配置或凭据。

### 4.3 Success Response

保留现有统一响应 envelope：

```json
{
  "success": true,
  "data": {
    "conversation_id": "conv-...",
    "status": "completed",
    "final_answer": "...",
    "turns": 3,
    "primary_task_id": "pubmed-...",
    "task_ids_by_source": {"pubmed": "pubmed-..."},
    "current_turn_lead_ids": ["pubmed-..."],
    "context_lead_ids": ["pubmed-..."],
    "tools_used": ["search_pubmed"],
    "sources_used": ["pubmed"],
    "artifacts": [
      {"source": "pubmed", "kind": "run_report", "name": "pubmed_run_report_...json"}
    ],
    "result_summary": {
      "lead_count": 1,
      "persisted_lead_count": 1
    }
  },
  "error": null,
  "request_id": "req-..."
}
```

本阶段是同步接口，`status` 只使用 `completed` 或 `failed`。

## 5. 路由与业务边界

Agent Router 只负责：

```text
请求校验
-> 调用 Runtime
-> 调用结果持久化桥接
-> 转换 API 响应
```

Agent Router 不负责：

- 直接调用 PubMed、OpenAlex、Crossref、NIH RePORTER 或 SMTP。
- 直接拼写 SQL。
- 再调用一次 LLM 总结结果。
- 从 `final_answer` 猜 Lead ID。
- 按用户文本做 `if "PubMed" in message` 这类 Tool 分支。

建议文件：

```text
src/scholarlead_agent/api/routers/agent.py
src/scholarlead_agent/api/schemas/agent.py
src/scholarlead_agent/services/agent_result_persistence.py
tests/test_api_agent.py
tests/test_agent_result_persistence.py
```

并在 `src/scholarlead_agent/api/app.py` 注册新 Router。

## 6. 错误处理与安全边界

复用既有 `ApiError` envelope，但 Agent 路由不得将模型、Tool、数据库或 Provider 的原始异常文本直接返回。

建议安全错误码：

```text
INVALID_AGENT_REQUEST
MODEL_NOT_CONFIGURED
AGENT_RUN_FAILED
AGENT_MAX_TURNS_EXCEEDED
AGENT_RESULT_PERSISTENCE_FAILED
```

响应中不得包含：

- API Key、SMTP 密码、模型 Provider 凭据。
- 数据库路径、stack trace、原始内部异常。
- 完整 Prompt 或未脱敏的完整 Tool 参数。
- raw/processed 文件的绝对路径。

现有全局未处理异常行为也应在本阶段审查：Agent 路由应返回安全的通用错误信息，而非 `str(exception)`。

邮件边界不变：

```text
Agent 可以调用 generate_email_draft。
Agent 不可以发送、批量发送、审批或调用 SMTP。
```

## 7. 测试策略

### 7.1 必须先做 Mock 测试

自动化测试必须使用 Mock Model 和 Mock Tool/Service，不得访问真实 LLM、PubMed、SMTP 或任何真实网络。

至少覆盖：

1. 新对话返回非空 `conversation_id` 和完成结果。
2. 追问复用同一 `conversation_id`，且历史消息可读取。
3. Mock Tool 调用返回 `tools_used`、`sources_used`、本轮 Lead ID 和安全 artifact 元数据。
4. 结果持久化桥接复用既有函数，返回 Lead 可被既有 Lead API 查询。
5. 上轮 Lead 不会混入本轮 `current_turn_lead_ids`，除非本轮确实再次产生。
6. 多来源结果返回 `task_ids_by_source`，不伪造单一 task ID。
7. 空输入、超长输入、非法 `max_turns` 返回 `INVALID_AGENT_REQUEST`。
8. 模型配置错误、模型异常、最大轮数错误都返回安全错误，不泄露密钥或 traceback。
9. Agent Tool Registry 中不存在发送邮件工具。
10. 既有 PubMed、Agent、API、邮件、前端测试全部回归通过。
11. `npm run build` 必须通过。
12. 完成一次 Vue Agent 页面 smoke test：Mock/API 响应可显示，`conversation_id` 可被下一轮复用，且有 Lead 时可进入或刷新已有客户列表。

不强制在本阶段新增 Playwright、Cypress 或其他自动化前端测试框架。自动化前端测试按当前项目既有测试体系补充；现有 Python 前端骨架测试应继续回归通过。

### 7.2 一次明确的真实小范围验证

所有 Mock 测试通过后，开发人员可在已配置模型与公开数据访问的前提下运行一次小范围真实验证：

```text
自然语言中明确要求“最多 3 篇”或“最多 5 篇”
仅一个明确的 PubMed 为主任务
不发送邮件
```

`max_results` 不是 `/api/agent/run` 的参数，而是 Agent 调用 PubMed Tool 时生成的 Tool 参数。真实验证应检查实际 Tool 调用的 `max_results <= 5`。Agent API 必须通过通用 `ToolContext(max_results_limit=5)` 将任何符合整数类型的 `max_results` 收紧为 5；该机制由 ToolRegistry 在调用前执行，不与 PubMed Tool 名称耦合。自然语言约束和执行后审计仍作为补充，不能替代执行上限。

核对：

- Agent 实际调用 Tool。
- Conversation 与 TaskContext 已持久化。
- PubMed 成功时，task/paper/Lead 能通过已有 API 查询。
- 返回 Lead ID 与数据库可查询 Lead 一致。
- 未发送任何邮件。

## 8. 实施步骤

1. 阅读 Runtime、Context、ToolRegistry、API Error、PubMed 持久化、Lead Router 和 Vue 占位代码。
2. 定义最小 Request/Response Schema 与安全输入限制。
3. 实现结果持久化桥接，复用既有 helper。
4. 实现调用 `run_agent_conversation()` 的 Agent Router。
5. 注册 Router，并完善 Agent 路由的安全错误转换。
6. 在现有 Vue API 模块中增加 `runAgent()`，替换占位处理函数。
7. 增加 Mock 单元、API、前端最小测试。
8. 在 `frontend` 目录运行构建，并完成 Vue Agent 页面 smoke test：

```powershell
npm run build
```

9. 先运行聚焦测试，再运行全量回归：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

10. 仅在明确人工确认和环境配置完成后，执行一次真实小范围验证。
11. 验收后更新项目状态和验收矩阵。

## 9. 验收矩阵

### API 与 Agent

- [ ] 已注册 `POST /api/agent/run`。
- [ ] Request Schema 校验 message 和 `max_turns`。
- [ ] 路由调用既有 `run_agent_conversation()`。
- [ ] 路由中没有直接科研数据调用或直接 SQL。
- [ ] 响应使用现有统一 success/error envelope。

### 结果完整性与持久化

- [ ] 返回 `conversation_id`、`final_answer`、`tools_used`、`sources_used`。
- [ ] `current_turn_lead_ids` 与累计上下文 Lead ID 分离。
- [ ] 多来源使用 `task_ids_by_source`，不伪造全局 task ID。
- [ ] 支持的结果通过既有 helper 持久化。
- [ ] 返回的已持久化 Lead ID 可通过既有 Lead API 查询。
- [ ] 仅在持久化成功后返回 persisted Lead ID；持久化失败不返回未入库 Lead。
- [ ] 同一 `idempotency_key` 的重试不会重复创建业务记录或草稿。
- [ ] artifact 不暴露绝对本地路径。

### Vue 最小入口

- [ ] 现有 Agent 对话页不再返回占位提示。
- [ ] 页面调用新 API，并在浏览器会话中复用 `conversation_id`。
- [ ] 页面展示结构化结果，并能进入已有 Lead 视图。

### 安全与测试

- [ ] 未新增 Agent 可调用的发送或 SMTP Tool。
- [ ] Agent API 错误已脱敏。
- [ ] Mock API 测试覆盖新对话、追问、Tool 结果、持久化、非法输入、模型异常与轮数限制。
- [ ] `npm run build` 通过，且 Vue Agent 页面 smoke test 通过。
- [ ] 自动化前端测试按现有测试体系覆盖，不强制为本阶段新增前端 E2E 框架。
- [ ] 全量 pytest 回归通过。
- [ ] 一次有限真实验证已单独记录，实际 PubMed Tool 参数 `max_results <= 5`，且未发送邮件。

## 10. 完成定义

当用户能够在现有 Vue Agent 对话页输入中文或英文科研线索需求，系统调用真实 Agent Runtime，返回结构化结果；在来源支持的情况下将本轮 Lead 持久化并可查询；用户可带同一 `conversation_id` 继续追问；且 Agent 始终无法触发邮件发送时，Stage 39 才视为完成。
