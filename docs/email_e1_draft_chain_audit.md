# Email-E1：邮件链路审计与测试基线

日期：2026-08-28  
状态：Completed  
范围：邮件草稿生成、批量草稿、审核、权限、发送、导出、FastAPI、Vue 与测试  
结论：现有链路稳定；Email-E2 可以在现有结构上增量实施。

## 1. 当前真实链路

```text
PubMedLead
-> build_auto_email_draft_input_from_lead
-> ServiceMatcher
-> SenderProfile
-> EmailDraftInput
-> EmailDraftService
-> ModelClient
-> parse_email_draft_model_output
-> EmailDraft(review_pending)
-> email_drafts
-> Batch Review / Permission
-> Controlled Send
-> email_send_logs / Result Package
```

## 2. 当前接口确认

| 接口 / 模块 | 当前职责 | v2.9 影响 |
| --- | --- | --- |
| `EmailDraftInput` | 草稿 Evidence 输入；`target_service_type` 必填。 | Email-E4 需向后兼容地加入 capability 字段，并解除对 Service Match 的硬依赖。 |
| `EmailDraft` | 草稿主体、来源、审核人、warnings、发送标记。 | Email-E6/E7 需增加或关联质量与版本信息。 |
| `EmailDraftService.generate` | 调用模型并构建 review-pending 草稿。 | Email-E5/E6 可在此处接入 Prompt v2 与一次重生成。 |
| `build_auto_email_draft_input_from_lead` | 先匹配业务服务，再注入 SenderProfile。 | Email-E4 需改为并行读取 Service Match 与 Capability Match。 |
| `match_company_service` | 确定性返回一个最佳业务服务。 | 保留，不用作 CapabilityMatcher 替代品。 |
| `load_sender_profile` | 读取固定、非密钥发件资料。 | Email-E2/E5 扩展 `intro_style` 等授权信息。 |
| `generate_batch_email_drafts` | 为 lead 批量生成并保存草稿。 | Email-E7 复用，不另建批量系统。 |
| `apply_batch_email_review` | 批量保存人工审核决定。 | 保留为真实发送前审核。 |
| `send_batch_reviewed_emails` | Permission / Test / Real Recipient 受控发送。 | 不改变安全边界。 |

## 3. 当前数据与持久化

SQLite 已有：

```text
email_drafts
email_reviews
email_send_logs
```

`email_drafts.payload_json` 已保存草稿 Evidence，适合过渡期兼容；但它不等同于完整的 Capability Match、Quality Report 或不可变草稿版本。

Email-E2 到 E7 的建议扩展顺序：

```text
sender_capabilities.json
-> capability_matches / capability_match_items
-> EmailDraftInput v2
-> email_draft_quality
-> draft version strategy
-> Result Package / API / Vue fields
```

## 4. 当前 API 与 Vue 状态

后端已有草稿列表、详情、批量生成、批量审核、受控发送和发送日志接口。

Vue 已能读取草稿、选择草稿、批量审核和受控发送；但尚未接入批量草稿生成按钮，且不展示正文、Evidence、质量报告、能力匹配或版本历史。

后续应扩展当前 API 和 Vue，不新建第二个邮件工作台。

## 5. 当前测试基线

全量命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

结果：`356 passed, 1 warning`。

邮件相关测试使用 Fake Model、模拟 SMTP 或本地 SQLite；本次测试未调用真实模型、真实 SMTP 或真实网络。

## 6. Email-E2 的可执行范围

Email-E2 可以直接开始，范围限定为：

1. 将已确认的 `sender_capabilities.json` 放入 `data/config/`；
2. 新增配置加载、schema 校验和版本读取；
3. 增加 Catalog 相关单元测试；
4. 不接入模型、不调用真实网络、不调用 SMTP；
5. 不提前实现 CapabilityMatcher、paper_only、Prompt v2、Quality Validator、数据库迁移、API 或 Vue 改造。

## 7. 本阶段验收

- 已确认现有数据结构、函数接口和模块位置；
- 未重写或破坏现有草稿、审核、权限、发送和导出实现；
- 已确认 E2-E8 的增量扩展位置；
- 全量 pytest 通过；
- 未访问真实网络；
- 未新增业务功能；
- 下一步为 Email-E2。
