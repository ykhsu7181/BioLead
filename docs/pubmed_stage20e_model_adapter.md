# PubMed 阶段 20E：OpenAI-compatible 模型适配器

日期：2026-08-20

## 1. 阶段目标

阶段 20E 的目标是给 Agent Loop 增加真实 OpenAI-compatible Chat Completions 模型边界。

本阶段只实现模型适配器，不执行真实模型 smoke test，不进入阶段 20F，不做邮件草稿，不发送邮件。

## 2. 新增模块

新增：

```text
src/scholarlead_agent/adapters/openai_compatible_chat.py
```

核心对象：

- `OpenAICompatibleChatAdapter`
- `LLMAdapterError`
- `LLMConfigError`
- `LLMRequestError`

## 3. 内部模型契约补充

`ModelReply` 新增：

- `usage`
- `model`

新增：

- `ModelUsage`

字段：

- `input_tokens`
- `output_tokens`
- `total_tokens`

## 4. 配置

新增环境变量：

```text
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
OPENAI_FALLBACK_MODEL=
```

这些配置集中在 `config.py` 中读取。

`.env.example` 只保留空占位，不写真实密钥。

## 5. Adapter 行为

Adapter 负责：

```text
内部 messages / tools
→ OpenAI-compatible /chat/completions
→ 内部 ModelReply
```

归一化内容包括：

- assistant content
- tool_calls
- tool_call_id
- finish_reason
- usage
- model
- provider request failure

Tool Call 的 `arguments` 保持模型原始 JSON 字符串，不在 Adapter 层做业务 Schema 校验。

## 6. 错误和重试

当前规则：

- 缺少配置抛出 `LLMConfigError`
- 网络错误抛出 `LLMRequestError`
- 认证错误、参数错误等 4xx 不重试
- 429 和 5xx 按项目 `retry_count` 有限重试
- 不在 Agent Loop 中做供应商 HTTP 重试
- 错误信息不打印完整 API Key

## 7. 测试

新增：

```text
tests/test_llm_adapter.py
```

覆盖：

- 普通文本回复；
- 单 Tool Call；
- 多 Tool Calls；
- tool_call_id 保留；
- finish_reason；
- usage 归一化；
- API 错误；
- 缺失字段；
- 配置缺失；
- 不泄露 API Key；
- retryable HTTP 状态有限重试。

测试全部使用 Fake Session，不访问真实模型 API。

## 8. 验收状态

已完成。

验证结果：

- LLM Adapter 测试：`9 passed`
- Agent / Tool / Adapter 组合测试：`39 passed`
- PubMed Service / CLI / UI 相关测试：`13 passed`
- 全量 pytest：`162 passed`

## 9. 已知限制

- 当前没有真实模型 smoke test；
- 当前不实现模型切换 UI；
- 当前不记录 Token 日志，完整日志留到阶段 20H；
- 当前不生成邮件草稿；
- 当前不发送真实邮件。
