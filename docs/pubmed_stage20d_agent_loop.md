# PubMed 阶段 20D：正式 Agent Loop

日期：2026-08-20

## 1. 阶段目标

阶段 20D 的目标是把正式 Agent Loop 放进当前项目结构中。

本阶段只实现 Loop 本身，不接真实 LLM，不实现 DeepSeek / OpenAI-compatible Adapter，不生成邮件草稿，不发送邮件。

## 2. 新增模块

新增：

```text
src/scholarlead_agent/agent/model.py
src/scholarlead_agent/agent/messages.py
src/scholarlead_agent/agent/loop.py
```

## 3. 核心对象

`model.py`：

- `ModelReply`
- `ModelClient`

`loop.py`：

- `AgentRunner`
- `AgentRunResult`
- `AgentRunError`
- `AgentLimitError`
- `IncompleteModelReplyError`
- `DEFAULT_SYSTEM_PROMPT`

## 4. Loop 流程

当前流程：

```text
user message
→ model.complete(messages, tools)
→ assistant reply
→ 如果没有 tool_calls，返回最终答案
→ 如果有 tool_calls，先保存 assistant message
→ ToolRegistry.prepare(...)
→ ToolRegistry.invoke(...)
→ tool result 按 tool_call_id 回填
→ 下一轮 model.complete(...)
```

## 5. 硬边界

当前 Loop：

- 有 `max_turns` 上限；
- 每轮都从 Registry 获取模型可见工具；
- 支持一个 assistant message 中多个 tool calls；
- 每个 tool call 都有且只有一个 tool result；
- tool result 保留原始 `tool_call_id`；
- Tool 错误也作为 tool result 回填；
- 没有写死 PubMed / Crossref / Email 分支；
- 不访问真实模型 API。

## 6. System Prompt 第一版

Prompt 说明：

- ScholarLead Agent 的用途；
- 需要真实文献数据时使用 Tool；
- PubMed 临时评分不是正式四维评分；
- 不伪造邮箱、基金和来源；
- 信息不足时说明或追问；
- 当前不能发送真实邮件。

Prompt 不是权限边界，后续真实邮件发送必须走代码级权限策略。

## 7. 测试

新增：

```text
tests/test_agent_loop.py
```

覆盖：

- 模型直接回答；
- 一次 Tool Call；
- Tool 后模型给最终答案；
- Tool 错误后模型继续；
- 多个 tool_calls 的 ID 配对；
- 未知 Tool；
- max turns；
- 空 final reply；
- 模型异常；
- 缺失 tool_call_id；
- Loop 源码不包含具体 Tool 分支。

## 8. 验收状态

已完成。

验证结果：

- Agent Loop 测试：`10 passed`
- Registry + Loop 测试：`22 passed`
- 全量 pytest：`153 passed`

## 9. 已知限制

- 使用 Fake Model 测试；
- 暂无真实 LLM；
- 暂无模型适配器；
- 暂无权限审批系统；
- 暂无邮件草稿；
- 暂无真实邮件发送。
