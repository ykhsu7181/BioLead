# PubMed 第一轮阶段 20H：首次 LLM Token / 模型调用记录

## 本阶段目标

从第一次正式 AI 功能开始，记录模型调用情况。

本阶段做的是最小可追踪日志，不是最终后台管理系统，也不是完整费用管理系统。

## 已完成内容

1. 新增 AI 使用记录数据结构。
2. 新增模型调用包装器，成功和失败调用都会记录。
3. Agent 自然语言模块记录为 `agent_reasoning`。
4. 邮件草稿模块记录为 `email_draft`。
5. Token 不再被适配器丢掉，继续保存在 `ModelReply.usage`。
6. 模型配置集中到 `config.py` 和 `ai/model_config.py`。
7. 支持不同功能模块配置默认模型。
8. Streamlit 增加“AI 使用情况”只读区域。
9. 测试中使用 Fake Model，不访问真实模型。

## 新增模块职责

`src/scholarlead_agent/ai/model_config.py`

- 定义功能模块名：
  - `agent_reasoning`
  - `email_draft`
  - `customer_analysis`
  - `score_explanation`
  - `report_generation`
- 根据功能模块选择默认模型。
- 返回不含 API Key 的模型运行配置。

`src/scholarlead_agent/ai/usage.py`

- 定义 `AIUsageRecord`。
- 定义 `UsageTrackingModelClient`。
- 保存 JSONL 使用记录。
- 读取最近使用记录。
- 汇总调用次数、成功/失败次数、Token 总量和已知费用。
- 费用未知时不猜测。

## 使用记录保存位置

默认保存到：

```text
data/processed/ai_usage/
```

文件格式：

```text
ai_usage_YYYYMMDD.jsonl
```

每一行是一条模型调用记录。

该目录属于生成数据，已经被 `.gitignore` 中的 `data/processed/*` 覆盖，不会提交。

## 记录字段

每次模型调用至少记录：

- `usage_id`
- `account_alias`
- `provider`
- `called_at`
- `feature_module`
- `model_name`
- `input_tokens`
- `output_tokens`
- `total_tokens`
- `estimated_cost`
- `currency`
- `pricing_config_version`
- `status`
- `error_type`
- `error_message`
- `task_id`
- `lead_id`
- `started_at`
- `finished_at`
- `latency_ms`

## 不记录的内容

日志不保存：

- API Key
- 完整 Prompt
- 完整模型回复正文
- 邮件正文
- PubMed 原始数据

这样做是为了先满足 Token / 模型调用追踪，同时减少敏感信息进入日志。

## 模型配置

`.env.example` 已补充：

```text
OPENAI_PROVIDER=openai_compatible
OPENAI_ACCOUNT_ALIAS=default
AGENT_DEFAULT_MODEL=
EMAIL_DRAFT_DEFAULT_MODEL=
AI_USAGE_DIR=data/processed/ai_usage
TOKEN_WARNING_THRESHOLD=
COST_WARNING_THRESHOLD=
AI_PRICING_CONFIG_VERSION=unconfigured
```

模型选择规则：

1. Agent 自然语言优先使用 `AGENT_DEFAULT_MODEL`。
2. 邮件草稿优先使用 `EMAIL_DRAFT_DEFAULT_MODEL`。
3. 如果功能默认模型为空，则回退到 `OPENAI_MODEL`。

## 费用估算

当前没有内置真实价格表。

如果没有明确价格配置：

```text
estimated_cost = null
currency = null
```

不会凭空猜价格，也不会声称费用准确。

## Streamlit 查看方式

启动页面后，展开：

```text
AI 使用情况
```

可以看到最近调用：

- 调用时间
- 功能模块
- 模型名称
- Token 用量
- 预估费用
- 状态

复杂筛选、账号统计、费用提醒属于后续后台模块。

## 阈值提醒状态

当前已经预留配置：

- `TOKEN_WARNING_THRESHOLD`
- `COST_WARNING_THRESHOLD`

但正式提醒机制尚未完成：

```text
threshold notification = pending final admin module
```

## 测试

新增：

```text
tests/test_ai_usage.py
```

扩展：

```text
tests/test_llm_adapter.py
```

覆盖内容：

- usage 正常保存；
- Token 缺失；
- 失败调用也有记录；
- API Key 不进入日志；
- 模型名称正确；
- feature_module 正确；
- 费用价格未知；
- 多次调用累计统计；
- Agent 和 email draft 可分别记录；
- 文件写入稳定；
- 功能模块默认模型选择。

## 已知限制

1. 当前使用 JSONL 文件，没有数据库。
2. 当前没有后台筛选页面。
3. 当前没有正式阈值提醒。
4. 当前没有管理员价格配置页面。
5. 费用估算只有在显式配置价格表时才会计算。

## 阶段验收

阶段 20H 已达到实施方案的最小验收要求：

- 每次默认正式 LLM 调用会写 usage；
- Agent 和邮件草稿模块可以区分；
- Token 字段保留；
- API Key 不写入日志；
- 模型配置集中；
- 支持功能级默认模型；
- Streamlit 可查看最近调用记录；
- 明确标记阈值提醒仍待后台阶段完善。
