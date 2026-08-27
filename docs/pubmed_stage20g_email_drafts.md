# PubMed 第一轮阶段 20G：个性化英文邮件草稿最小版

## 本阶段目标

补齐 T+30 主链路里的“客户详情 -> 个性化英文邮件草稿”能力。

本阶段只生成草稿，给人工查看和编辑，不实现真实发送、不批量发送、不自动审批。

## 已完成内容

1. 新增邮件草稿 Prompt 与数据结构。
2. 新增 EmailDraftService，通过模型适配器生成英文草稿。
3. 新增 Agent Tool：`generate_email_draft`。
4. 默认 Agent Registry 已注册 `search_pubmed` 和 `generate_email_draft`。
5. Streamlit 的 Lead 详情页支持生成、查看、人工编辑和下载草稿 JSON。
6. 测试全部使用 Fake Model，不访问真实 LLM。

## 新增模块职责

`src/scholarlead_agent/ai/email_drafts.py`

- 定义 `EmailDraftInput` 和 `EmailDraft`。
- 存放邮件草稿 Prompt。
- 构造模型输入 evidence。
- 解析模型输出的 subject / body。
- 输出结构化草稿字典。

`src/scholarlead_agent/services/email_draft_service.py`

- 调用模型适配器生成草稿。
- 把模型输出转换成结构化 `EmailDraft`。
- 统一处理模型异常。

`src/scholarlead_agent/tools/email_draft_tool.py`

- 给 Agent 暴露 `generate_email_draft` 工具。
- 校验工具参数。
- 返回结构化 ToolResult。
- 不包含任何发送邮件动作。

## 草稿字段

当前 `EmailDraft` 至少包含：

- `lead_id`
- `subject`
- `body`
- `language`
- `draft_status`
- `generated_at`
- `model_name`
- `source_paper_title`
- `source_pmid`
- `doi`
- `source_url`
- `target_service_type`
- `human_reviewer`
- `reviewed_at`
- `recipient_name`
- `verified_email`
- `email_status`
- `evidence`
- `warnings`
- `can_send`

## 当前状态规则

- `draft_status = review_pending`
- `can_send = false`
- 无公开邮箱时仍可生成草稿，但会加入 `missing_verified_email` warning。
- 无 abstract 时仍可生成草稿，但会加入 `missing_abstract` warning。
- 所有草稿都需要人工审核。

## Prompt 边界

Prompt 明确要求：

- 只能使用提供的 evidence；
- 不编造基金；
- 不编造实验结果；
- 不编造邮箱；
- 不把候选 PI 说成绝对确认；
- 不自动发送邮件；
- 输出英文；
- 输出结构化 subject / body。

## Streamlit 使用方式

1. 先运行 PubMed 检索。
2. 打开 `Lead 详情`。
3. 选择一个 Lead。
4. 展开 `英文邮件草稿`。
5. 填写或确认 `target_service_type`。
6. 点击 `生成英文邮件草稿`。
7. 查看并编辑 `subject` 和 `body`。
8. 可下载草稿 JSON。

本阶段没有发送按钮。

## 测试

新增测试：

- `tests/test_email_drafts.py`
- `tests/test_email_draft_tool.py`

扩展测试：

- `tests/test_agent_runtime.py`
- `tests/test_tool_registry.py`

覆盖内容：

- 输入 evidence 构造；
- 无 abstract；
- 无 verified email；
- funding 未接入时不提供虚构 funding；
- 输出 `EmailDraft` 字段；
- `draft_status`；
- `model_name`；
- 模型异常；
- Prompt 不包含 API Key；
- Registry 支持 keywords 数组；
- 不存在 `send_email` 工具。

## 已知限制

1. 草稿目前只保存在 Streamlit 当前会话或下载 JSON，没有写入数据库。
2. 草稿质量依赖模型能力，需要人工检查。
3. 还没有批量生成草稿。
4. 还没有审批流。
5. 还没有真实邮件发送能力。

## 阶段验收

阶段 20G 已达到当前实施方案的最小验收要求：

- 可基于 Lead / paper / abstract / service_type 生成英文草稿；
- 草稿有结构化状态；
- 支持人工查看和编辑；
- 记录模型名称和生成时间；
- 不实现真实发送；
- 自动化测试不访问真实网络或真实模型。
