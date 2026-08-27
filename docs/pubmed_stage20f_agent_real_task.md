# PubMed 阶段 20F：Agent 真实任务测试与前端接入

日期：2026-08-20

## 1. 阶段目标

阶段 20F 的目标是让自然语言 Agent 入口可以连接：

```text
自然语言
→ Agent Loop
→ ToolRegistry
→ search_pubmed
→ PubMed Service
→ Tool Result
→ 最终回答
```

本阶段不进入阶段 20G，不生成邮件草稿，不发送真实邮件。

## 2. 新增入口

新增 CLI Agent 入口：

```text
src/scholarlead_agent/agent_main.py
```

运行方式：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.agent_main "自然语言任务"
```

新增 Agent 运行装配：

```text
src/scholarlead_agent/agent/runtime.py
```

包含：

- `build_default_tool_registry()`
- `build_default_model_client()`
- `run_agent_task(...)`
- `extract_tool_names(...)`
- `extract_run_report_paths(...)`

## 3. Streamlit 接入

Streamlit 页面新增：

```text
Agent / 自然语言任务
```

保留原有手动 PubMed 检索表单。

Agent 区域展示：

- 自然语言输入框；
- 运行按钮；
- 最终回答；
- 调用过的 Tool；
- Run Report 路径；
- Agent messages。

页面不显示 API Key。

## 4. 测试

新增：

```text
tests/test_agent_runtime.py
tests/test_agent_main.py
```

测试覆盖：

- 默认 Registry 注册 `search_pubmed`；
- Fake Model 触发 `search_pubmed`；
- 不需要 Tool 的问题不强制调用 PubMed；
- CLI Agent 输出摘要；
- CLI Agent 错误返回；
- Streamlit Agent helper 可用。

## 5. Smoke Test 文档

新增：

```text
docs/pubmed_agent_smoke_test.md
```

记录 10 个代表性真实任务测试项。

当前真实模型 smoke test 未自动执行，需要本地配置 `OPENAI_*` 后手动运行。

## 6. 验收状态

已完成。

验证结果：

- Agent runtime / CLI 测试：`5 passed`
- Streamlit UI 测试：`5 passed`
- Agent / Tool / Adapter / Registry 组合测试：`44 passed`
- 全量 pytest：`168 passed`

## 7. 已知限制

- 自动化测试使用 Fake Model；
- 没有在 pytest 中访问真实模型；
- 没有在 pytest 中访问真实 PubMed；
- 真实 smoke test 需要用户本地配置模型密钥；
- 不生成邮件草稿；
- 不发送真实邮件。
