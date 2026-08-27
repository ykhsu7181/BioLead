# PubMed 阶段 20C：Python ToolRegistry

日期：2026-08-20

## 1. 阶段目标

阶段 20C 的目标是建立统一 Tool 注册、模型暴露、参数准备、Schema 校验和执行机制。

本阶段不实现 Agent Loop，不接入 LLM，不生成邮件草稿，不发送邮件。

## 2. 新增模块

新增：

```text
src/scholarlead_agent/agent/registry.py
```

核心对象：

- `ToolContext`
- `PreparedToolCall`
- `ToolPreparationResult`
- `ToolRegistry`

## 3. Registry 职责

`ToolRegistry` 支持：

- `register(tool)`
- `snapshot()`
- `to_model_tools()`
- `prepare(tool_call, context=None)`
- `invoke(prepared_call, context=None)`

## 4. prepare / invoke 分离

`prepare(...)` 只做：

- 查找 Tool；
- 解析 arguments JSON；
- 判断 arguments 是否为 object；
- 做 Schema 校验；
- 返回 `PreparedToolCall` 或结构化错误。

`invoke(...)` 只执行已经准备好的 Tool Call。

Registry 中没有写：

```python
if tool_name == "search_pubmed":
    ...
```

新增 Tool 的方式是：

```text
定义 Tool
→ registry.register(tool)
```

## 5. 模型可见 Tool Schema

`to_model_tools()` 只暴露：

- `name`
- `description`
- `parameters`

不会暴露：

- handler
- secret
- API Key

## 6. 错误结构

当前 prepare 错误包括：

- `invalid_tool_call`
- `unknown_tool`
- `invalid_arguments`

当前 invoke 错误包括：

- `invalid_prepared_call`
- `tool_execution_error`
- `invalid_tool_result`

## 7. Tool Context 预留

`ToolContext` 预留：

- `workspace`
- `task_id`
- `run_id`
- `identity`
- `idempotency_key`

本阶段不把 API Key 或敏感信息放进模型可见参数。

## 8. 测试

新增：

```text
tests/test_tool_registry.py
```

覆盖：

- 正常注册；
- 重复 Tool；
- 注册 `search_pubmed`；
- 未知 Tool；
- 非法 JSON；
- 非 object 参数；
- Schema 失败；
- OpenAI 风格 tool call；
- 正常 invoke；
- Handler 异常；
- Handler 返回非法结果；
- 模型暴露 schema 不包含 handler。

## 9. 验收状态

已完成。

验证结果：

- Registry 测试：`12 passed`
- Tool + Registry 测试：`20 passed`
- 全量 pytest：`143 passed`

## 10. 已知限制

- 暂无 Agent Loop；
- 暂无 LLM 调用；
- 暂无权限审批系统；
- 暂无审计落库；
- 暂无真实邮件发送。
