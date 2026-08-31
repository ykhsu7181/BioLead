# Stage 39A-lite 项目状态轻量审计

日期：2026-08-28  
范围：Stage 30-38 当前代码、测试、API、Vue 覆盖与风险基线  
执行结果：通过审计；可进入 Email-E2，未新增业务功能。

## 1. 审计方法

本次检查了项目规范、当前状态、验收矩阵、v2.8 主线、v2.9 邮件专项、`src/`、`tests/`、FastAPI 路由、Vue 前端和配置目录。

全量回归命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

结果：356 passed，1 个第三方 `StarletteDeprecationWarning`，无失败。

## 2. 已实现并有测试的基础

| 范围 | 当前结论 |
| --- | --- |
| 数据主链路 | PubMed 是主链路；Crossref、OpenAlex、NIH RePORTER 有第一版集成。 |
| 数据与证据 | 已有统一模型、EvidenceRecord、SQLite、raw/processed 输出和 Result Package v2。 |
| Agent | 已有 ToolRegistry、有限轮次 AgentRunner、模型适配器和最小 Conversation Context。 |
| 邮件草稿 | 已有 `EmailDraftInput`、`EmailDraft`、模型调用、JSON 解析、固定 SenderProfile 和人工审核草稿状态。 |
| 发送边界 | 已有 Review、Permission、SMTP 测试发送、批量审核、受控批量发送、额度/幂等/日志相关基础。 |
| 后端 | FastAPI 已注册 PubMed、Lead、Email Batch、Jobs、Result Package、Conversation 等路由。 |
| 前端 | Vue 已有 PubMed、Lead、Service Match、草稿列表、批量审核、受控发送和发送日志基础界面。 |
| 测试 | 356 项全量 pytest 通过；外部源测试采用 mock，不要求真实网络。 |

## 3. 部分实现或仍属基础版的范围

| 范围 | 当前状态 | 结论 |
| --- | --- | --- |
| Vue Agent | 有前端与后端基础，但多轮业务对话尚未成为稳定正式入口。 | 保持 Stage 39B 计划。 |
| 邮件运营 | 支持受控发送和日志，但不是生产级投递、退信、退订、抑制名单或活动治理系统。 | 保持 Stage 39C-1/39C-2 计划。 |
| 多源身份归并 | 保守第一版。 | 不应仅凭姓名自动合并。 |
| 正式评分 | 仍是最小证据版。 | 需后续正式业务规则。 |
| Data Source Adapter | 已有规范，但并非每个数据源都已完整迁移。 | 新源继续遵守 Stage 38 规范。 |

## 4. 当前邮件链路基线

```text
PubMedLead
-> ServiceMatcher
-> SenderProfile
-> EmailDraftInput
-> EmailDraftService / ModelClient
-> EmailDraft(review_pending)
-> SQLite email_drafts
-> Human Review / Permission
-> Controlled Send / email_send_logs
-> Result Package v2
```

关键实现位置：

| 职责 | 当前模块 |
| --- | --- |
| 草稿数据模型、Prompt、解析 | `src/scholarlead_agent/ai/email_drafts.py` |
| 草稿服务、ServiceMatcher/SenderProfile 注入 | `src/scholarlead_agent/services/email_draft_service.py` |
| 固定发件人资料 | `src/scholarlead_agent/sender_profile.py` |
| 业务服务匹配 | `src/scholarlead_agent/service_matching.py` |
| 批量草稿、审核、发送 | `src/scholarlead_agent/services/email_batch_service.py` |
| 审核与发送权限 | `src/scholarlead_agent/email_review.py` |
| SQLite 持久化 | `src/scholarlead_agent/database.py` |
| 邮件 API | `src/scholarlead_agent/api/routers/email_batches.py` |
| Vue 页面 | `frontend/src/App.vue`、`frontend/src/api.js` |
| 结果导出 | `src/scholarlead_agent/result_package.py` |

## 5. API 覆盖

当前已存在：

```text
GET  /api/email-drafts
GET  /api/email-drafts/{draft_id}
POST /api/email-drafts/batch-generate
POST /api/email-drafts/batch-review
POST /api/email-sends/batch-send
GET  /api/email-sends
```

当前边界正确：浏览器通过 FastAPI 调用后端，不直接访问模型、SMTP、PubMed 或 SQLite。

## 6. Vue 覆盖

当前 Vue 页面已能：

- 读取草稿和发送日志；
- 选择多个草稿；
- 提交批量审核；
- 发起 `permission_check`、测试收件人或真实收件人模式的受控发送请求；
- 显示草稿状态、主题和发送日志。

当前 Vue 页面尚不能：

- 从页面直接触发批量草稿生成；
- 展示完整草稿正文、论文摘要片段或草稿 Evidence；
- 展示或编辑 Capability Match、Quality Report、Prompt Version、Draft Version；
- 在页面内执行 v2.9 的重生成、`paper_only` 或质量失败处理。

## 7. 已确认的 Email-E2 至 Email-E8 缺口

### Email-E2：Sender Capability Catalog

- `data/config/` 当前只有 `company_services.csv` 与 `sender_profile.json`。
- 当前没有项目内 `sender_capabilities.json`、Catalog loader 或 schema validation。
- SenderProfile 只有姓名、职位、机构、邮箱、签名；尚无 `intro_style` 或 `I lead` 授权字段。

### Email-E3：CapabilityMatcher

- 当前只有 `service_matching.py`，没有独立 CapabilityMatcher。
- ServiceMatcher 返回单个最佳业务服务，不是 0-6 项能力候选列表。
- 当前 ServiceMatcher 的 `research_direction` 来自 `lead.target_service_type`，不适合直接作为 v2.9 邮件能力匹配的论文事实。

### Email-E4：EmailDraftInput v2 和 paper_only

- `EmailDraftInput.target_service_type` 当前是必填字段。
- `build_auto_email_draft_input_from_lead` 在无 Service Match 时会抛出 `EmailDraftGenerationError`。
- 因此当前不支持“无 Service Match 但仍基于能力草稿”或“0 项能力走 paper_only”。
- 需要以向后兼容方式新增 CapabilityMatch 引用、候选能力、状态、版本与可选论文方向字段。

### Email-E5：Prompt v2

- 当前 Prompt 已要求只使用输入证据、不编造基金/邮箱/机构等事实、返回 JSON。
- 当前尚未强制三段式、学术交流结尾、paper observation、能力约束、非销售语气或称呼 fallback。
- `parse_email_draft_model_output` 的最终 fallback subject 是 `Potential academic collaboration`，与 v2.9 的目标 subject 规则不一致。

### Email-E6：Quality Validator

- 当前没有 Draft Quality Report、`pass/warning/fail` 状态或最多一次自动重生成机制。
- 当前 `EmailDraft` 有一般 warnings，但没有能力声明、论文支撑、字数、段落、销售语气等自动检查。
- 当前 `email_sending_not_implemented` warning 与已有受控 SMTP 发送能力的实际状态不完全一致，后续应在不影响安全边界的前提下澄清语义。

### Email-E7：Batch Draft v2 和 Reviewer Workspace

- 当前批量草稿、批量审核、批量受控发送已经存在。
- 当前没有 Capability Match、Quality Report、Draft Version 的数据库结构、API 返回或 Vue 展示。
- `insert_email_draft` 对同一 `draft_id` 使用 upsert；尚无不可覆盖的草稿版本历史。

### Email-E8：Benchmark 和 E2E

- 当前没有邮件草稿 Golden Set、人工评分表、Prompt A/B 对比或 v2.9 指标导出。
- Result Package v2 目前导出 service match、email drafts、reviews、send logs；未导出 capability matches 或 draft quality。

## 8. 风险与处理原则

| 风险 | 处理原则 |
| --- | --- |
| 无 Service Match 目前会阻塞草稿 | Email-E4 改为 Capability Match / paper_only 分流，但不删除现有 ServiceMatcher。 |
| 能力被模型编造 | CapabilityMatcher 必须确定性匹配；模型只能表达已输入能力。 |
| `I lead` 夸大个人身份 | 仅当 SenderProfile 有明确、固定授权时允许。 |
| paper_only 变成泛化或虚假能力邮件 | 第二段仅允许固定、批准的通用 scientific interest。 |
| 质量检查无限调用模型 | fail 最多自动重生成一次；二次失败停止。 |
| 版本升级覆盖历史草稿 | 保存 capability match 引用及 Catalog、Matcher、Prompt、Draft 版本。 |
| 自动化绕过发送安全 | Capability Match 和 Quality 仅影响草稿；真实发送继续由既有 Review/Permission/Provider 边界控制。 |

## 9. 测试覆盖与缺口

当前邮件测试已覆盖草稿输入、模型失败、草稿工具、SenderProfile、Service Catalog、ServiceMatcher、审核、SMTP、发送、批量服务、数据库、结果包和部分 API / 前端骨架。

Email-E2 以后需要新增：

```text
Sender Capability Catalog schema / version / disabled capability tests
CapabilityMatcher 4-6 / 1-3 / 0 项测试
paper_only 输入与草稿测试
I lead 授权和称呼 fallback 测试
Prompt v2 与 JSON 解析失败测试
Quality pass / warning / fail / one regeneration / second-failure stop tests
CapabilityMatch、Quality、Draft Version 数据库迁移与 Result Package 测试
Email API 与 Vue 的草稿生成、详情、质量和版本展示测试
```

## 10. 下一步结论

Stage 39A-lite 与 Email-E1 已完成：当前代码边界清楚、全量测试通过、未发现阻止后续邮件专项开发的回归问题。

下一阶段：`Email-E2：Sender Capability Catalog 接入`。

Email-E2 只做能力目录文件进入项目配置、加载、校验、版本读取与测试；不提前实现 CapabilityMatcher、Prompt v2、Quality Validator 或 Vue 改造。
