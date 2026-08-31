# ScholarLead Agent 下一步开发计划（v2.8 修正版）

> 执行状态：Current Main Roadmap
>
> v2.7 中 Stage 30-38 已完成第一轮实现。
>
> 本文档从现在开始作为 Stage 39 及后续开发的主线路线图依据。
>
> 当前邮件草稿专项的实施入口为 `docs/ScholarLead_Agent_email_draft_improvement_plan_v2.9.md` 中的 Email-E1。该专项不替代本文件的 Stage 39-46 编号与安全约束。
>
> `docs/ScholarLead_Agent_next_plan_v2.7.md` 继续保留，仅作为 Stage 30-38 的设计与实施记录。

版本：v2.8-revised  
日期：2026-08-27  
项目：ScholarLead Agent / BioLead  
当前基线：Stage 38  
下一阶段入口：Stage 39A-lite

---

## 1. 文档定位

当前项目已经不再是早期 PubMed 单链路原型。Stage 38 后，项目已经具备：

```text
PubMed / Crossref / OpenAlex / NIH RePORTER
-> Unified Models / Evidence
-> Agent Loop / ToolRegistry
-> Conversation / Task Context
-> Company Service Catalog / ServiceMatcher
-> Email Draft / Human Review / Controlled Send
-> SQLite
-> Background Jobs
-> FastAPI
-> Vue Frontend
-> Result Package v2
-> Data Source Adapter Specification
```

因此 v2.8 不再以“继续堆功能数量”为主，而是转向：

```text
Integration
-> Safety
-> Validation
-> Productization
-> Data Source Expansion
```

简单说：先把现有主链路跑稳，再扩新数据源。

---

## 2. 当前真实状态

当前已经完成或具备第一版能力：

- PubMed 小范围真实检索。
- Crossref / OpenAlex / NIH RePORTER 查询。
- 公开邮箱提取。
- Paper / Lead / Researcher / Organization / Funding / Evidence 基础模型。
- AgentRunner / ToolRegistry。
- 最小 Conversation Context。
- Company Service Catalog。
- ServiceMatcher。
- SenderProfile。
- 自动邮件草稿。
- 人工 Review。
- SMTP 单封测试发送。
- Batch Draft。
- Batch Review。
- Controlled Batch Send。
- SQLite。
- jobs / job_items。
- Result Package v2。
- FastAPI。
- Vue 基础工作台。
- Data Source Adapter 规范。

当前主要缺口：

- Vue Agent 多轮对话还没有稳定成为正式业务入口。
- 批量邮件发送安全层还需要补齐。
- Company Service Catalog 需要更贴近公司真实业务。
- ServiceMatcher 需要人工标注样例验证。
- Researcher 身份归并仍然保守。
- 正式四维评分仍处于 provisional。
- Vue 还没有完整承接 Streamlit 的全部演示能力。
- 新数据源不应早于现有主链路 E2E 验收。

---

## 3. v2.8 修订原则

根据当前项目实际状态，本版计划做以下修订：

1. Stage 39A 不重复文档治理。
   - `current_project_status.md`
   - `feature_acceptance_matrix.md`
   - README / README_cn
   - AGENTS / AGENT_cn

   这些已经完成第一轮统一。

2. Stage 39A 改为轻量审计。
   - 只确认代码状态、测试状态、API 覆盖、Vue 覆盖和风险缺口。

3. Stage 39B 先做小闭环。
   - 不一开始追求复杂自然语言。
   - 先让 Vue 真正调用 FastAPI -> AgentRunner -> ToolRegistry。

4. Stage 39C 拆成两个小阶段。
   - 39C-1：基础批量邮件安全层。
   - 39C-2：增强身份门禁和发送治理。

5. Stage 39D 做业务目录扩充。
   - 邮件草稿必须基于已匹配业务，不允许重新猜业务。

6. Stage 39E 做真实 E2E 验收。
   - 先证明现有主链路能跑通，再接 ORCID、Europe PMC、bioRxiv / medRxiv 等新源。

---

## 4. 新阶段总览

推荐顺序：

```text
Stage 39A-lite：项目状态轻量审计与测试基线
Stage 39B：Vue Agent 小闭环真实接通
Stage 39C-1：批量邮件基础安全层
Stage 39C-2：批量邮件增强安全层
Stage 39D：公司业务目录扩充与 ServiceMatcher 验证
Stage 39E：真实 E2E 闭环验收

Stage 40：ORCID Researcher Identity Adapter
Stage 41：Researcher Resolution v2
Stage 42：bioRxiv / medRxiv Preprint Adapter
Stage 43：Europe PMC Adapter
Stage 44：Institution Public Profile Adapter
Stage 45：Official Scoring v1
Stage 46：Production Readiness Review
```

不建议在 Stage 39E 之前进入 Stage 40。

---

## 5. Stage 39A-lite：项目状态轻量审计与测试基线

### 5.1 目标

本阶段不新增业务功能，只确认 Stage 30-38 的真实代码状态。

重点回答：

```text
哪些功能已经有代码
哪些只是文档
哪些已经有 API
哪些已经迁移到 Vue
哪些有测试
哪些仍是 placeholder
哪些存在安全缺口
```

### 5.2 需要检查

```text
AgentRunner
ToolRegistry
Conversation Context
SQLite schema
ServiceMatcher
SenderProfile
EmailDraftService
Background Jobs
FastAPI
Vue
BatchDraft
BatchReview
BatchSend
Result Package v2
Data Source Adapter
```

### 5.3 输出文档

新增：

```text
docs/stage39a_project_audit.md
```

不再新增 `project_status_after_stage38.md`，避免和 `docs/current_project_status.md` 重复。

建议内容：

```text
Implemented
Partially Implemented
Placeholder
Not Implemented
Known Risks
Test Coverage
API Coverage
Frontend Coverage
Next Priority
```

### 5.4 测试基线

运行：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

如果存在回归失败：

```text
先修回归
不得进入 Stage 39B
```

### 5.5 验收

```text
1. Stage 30-38 状态逐项确认；
2. 全量 pytest 通过；
3. 生成 docs/stage39a_project_audit.md；
4. 明确 Vue Agent 是否仍为 placeholder；
5. 明确 Batch Send 当前安全缺口；
6. 不新增 Stage 40 数据源；
7. 不新增业务功能。
```

---

## 6. Stage 39B：Vue Agent 小闭环真实接通

### 6.1 目标

让 Vue Agent 区域真正调用：

```text
Vue
-> FastAPI
-> Conversation Context
-> AgentRunner
-> ToolRegistry
-> Tool Calls
-> Tool Results
-> Assistant Reply
```

第一版不追求复杂任务链，先跑通小闭环。

### 6.2 第一版任务范围

先支持两类最小任务：

```text
1. 检索 PubMed 小范围论文和候选 PI
2. 基于上一轮结果继续筛选，例如“只保留有公开邮箱的”
```

推荐测试句：

```text
帮我找 2025 年以来美国做 single-cell cancer 的 PubMed 论文，最多 5 篇，并列出有公开邮箱的候选 PI。
```

第二轮：

```text
只保留有验证邮箱的线索。
```

### 6.3 推荐接口

优先沿用 Conversation 资源：

```text
POST /api/conversations/{conversation_id}/run
```

Request：

```json
{
  "message": "找美国做 single-cell cancer 的 PI"
}
```

Response 建议：

```json
{
  "conversation_id": "conversation-xxx",
  "task_id": "task-xxx",
  "assistant_message": "...",
  "selected_lead_ids": [],
  "tool_summary": [],
  "status": "completed"
}
```

### 6.4 Vue 页面要求

展示：

```text
用户消息
Assistant 回复
conversation_id
当前 task_id
selected leads
简要 tool activity
错误状态
继续追问入口
```

禁止展示：

```text
API Key
SMTP 配置
完整 raw prompt
内部完整 Tool JSON
敏感数据库 payload
```

### 6.5 Context 规则

```text
system prompt
-> task context
-> recent messages
-> current user message
```

大结果处理：

```text
完整数据 -> SQLite / Artifact
LLM -> 摘要 + ID
```

### 6.6 后续增强目标

小闭环通过后，再扩展到五轮验收：

```text
1. 找 2025 年以来美国做 single-cell cancer 研究的 PI
2. 只保留有公开邮箱的
3. 只看有基金证据的
4. 给前三个人生成邮件草稿
5. 第二个人的论文、基金和匹配业务是什么？
```

### 6.7 安全要求

```text
Conversation 不能绕过 Permission
Agent 不允许因为用户要求而跳过 Review
模糊指代不能直接触发真实发送
send_email 仍不注册为普通 Agent Tool
```

### 6.8 验收

```text
1. Vue 不再调用 Agent placeholder；
2. Vue 真正调用 FastAPI Agent 接口；
3. 多轮 conversation_id 可用；
4. 第二轮可以引用第一轮结果；
5. 新会话隔离；
6. ToolCall 与 ToolResult 成对；
7. Fake Model 测试通过；
8. Streamlit 不被破坏。
```

---

## 7. Stage 39C-1：批量邮件基础安全层

### 7.1 目标

在扩大真实批量发送前，先补齐最基础的防重复和权限边界。

防止：

```text
同一邮箱重复发送
同一批次重复发送
崩溃后重复发送
超出每日额度
未通过 permission_check 却调用 provider
```

### 7.2 Idempotency

新增：

```text
idempotency_key
```

建议：

```text
hash(draft_id + normalized_recipient_email + draft_version)
```

同一个 key 只能产生一次有效发送。

### 7.3 Recipient 去重

发送前按：

```text
normalized_recipient_email
task_id / campaign_id
batch_id
```

检查：

```text
same email repeated
same email in same batch
same recipient already contacted in same campaign
```

### 7.4 Quota

配置：

```text
EMAIL_BATCH_MAX_SIZE
EMAIL_DAILY_LIMIT
EMAIL_SEND_INTERVAL_SECONDS
```

第一版继续保守，真实发送只允许小范围 smoke test。

### 7.5 Permission Boundary

要求：

```text
approved = true
verified email exists
EMAIL_SEND_ENABLED = true
permission_check passed
```

如果 permission_check 不通过：

```text
不得调用 provider
必须记录 blocked reason
```

### 7.6 验收

```text
1. idempotency 生效；
2. normalized email dedup 生效；
3. quota 生效；
4. permission_check 不通过时不调用 provider；
5. retry 不导致明显重复发送；
6. Fake Provider 测试通过；
7. 真实发送仍只做 controlled smoke test。
```

---

## 8. Stage 39C-2：批量邮件增强安全层

### 8.1 目标

在 39C-1 基础上，补齐更强的身份门禁和 suppression 机制。

防止：

```text
错误身份发送
Do Not Contact 对象继续发送
同一 PI 多 Lead 重复发送
同一邮箱对应多个研究者时误发
疑似身份冲突时自动发送
```

### 8.2 Suppression List

建议新增表：

```text
suppression_list
```

字段：

```text
suppression_id
normalized_email
reason
source
status
created_at
updated_at
```

reason：

```text
do_not_contact
manual_block
bounce
complaint
invalid_email
duplicate_identity
```

### 8.3 Researcher Identity Gate

自动进入发送边界前建议满足：

```text
researcher_resolution_status = resolved
email_name_match_confidence = high
manual_review_required = false
duplicate_candidate = false
```

以下进入：

```text
needs_review
```

```text
probable_match
conflicting_identity
duplicate_candidate
multiple_leads_same_email
multiple_researchers_same_email
```

### 8.4 Send 状态

```text
blocked
queued
sending
accepted
failed
bounced
needs_review
```

说明：

```text
SMTP success != delivered
```

只有 Provider 明确返回投递事件时才可使用：

```text
delivered
```

### 8.5 Retry

```text
认证失败 -> 不自动重试
配置错误 -> 不自动重试
明确 pre-send transient error -> 有限重试
可能已被服务端接受但 timeout -> needs_review，不自动重发
```

### 8.6 验收

```text
1. suppression 生效；
2. do_not_contact 生效；
3. 同 researcher 不重复发送；
4. unresolved researcher 不自动发送；
5. duplicate_candidate 不自动发送；
6. multiple_researchers_same_email 进入 needs_review；
7. bounce / complaint 可进入 suppression；
8. Fake Provider 测试通过。
```

---

## 9. Stage 39D：公司业务目录扩充与 ServiceMatcher 验证

### 9.1 目标

把 ServiceMatcher 从：

```text
算法可运行
```

推进到：

```text
业务覆盖接近真实公司
+
有人工 Ground Truth 验证
```

### 9.2 第一版 10 个测试业务

```text
S001 Genome De novo Assembly
S002 Long-read Variant Detection
S003 Full-length Transcriptome Sequencing
S004 Microbial Complete Genome Sequencing
S005 Hi-C Sequencing
S006 ATAC-seq
S007 Hi-R
S008 CUT&Tag
S009 Single-cell RNA Sequencing
S010 Spatial Transcriptomics
```

### 9.3 配置形式

优先使用结构化文件：

```text
data/config/company_services.xlsx
```

Sheet：

```text
Services
Keywords
Matching_Rules
Email_Talking_Points
```

运行时可：

```text
XLSX -> Import -> CompanyServiceCatalog
```

或：

```text
XLSX -> normalized CSV -> CompanyServiceCatalog
```

### 9.4 Ground Truth

至少准备：

```text
20-30 篇论文摘要
```

人工标记：

```text
expected_service_id
expected_status
review_note
```

示例：

```text
scRNA-seq tumor immune -> S009
Hi-C chromatin loop -> S005
Iso-Seq alternative splicing -> S003
CUT&Tag H3K27ac -> S008
spatial tumor niche -> S010
```

### 9.5 测试指标

记录：

```text
Top-1 Accuracy
Matched / No-match Accuracy
Needs-review Rate
Wrong-service Rate
```

### 9.6 验收

```text
1. 10 项业务成功加载；
2. 不修改核心算法即可换业务表；
3. catalog_version / matcher_version 保存；
4. 至少 20 篇人工标注摘要；
5. 低置信度进入 needs_review；
6. 错误匹配可解释；
7. 不允许 LLM 创造不存在的服务；
8. EmailDraft 使用已有 matched_service，不重新猜业务。
```

---

## 10. Stage 39E：真实 E2E 闭环验收

### 10.1 目标

证明一个真实 `task_id` 能贯穿完整主链路。

### 10.2 推荐任务

```text
query:
single-cell RNA sequencing cancer

时间：
近 2 年

max_results:
10-20
```

### 10.3 完整链路

```text
Vue
-> Agent
-> PubMed
-> Crossref
-> OpenAlex
-> NIH RePORTER
-> Lead
-> Researcher
-> Evidence
-> ServiceMatcher
-> Email Draft
-> Human Review
-> permission_check
-> 少量 test_recipient
-> Result Package v2
```

### 10.4 ID 追踪

从：

```text
task_id
```

追踪：

```text
PMID / DOI
lead_id
researcher_id
funding record
evidence record
service match
draft_id
review record
send log
package_id
```

### 10.5 新增报告

```text
docs/stage39e_e2e_validation_report.md
```

记录：

```text
Task
Environment
Inputs
Data Sources Queried
Counts
Generated Files
Service Match Results
Email Draft Results
Review Results
Send Boundary Results
Result Package
Known Issues
Final Status
```

### 10.6 验收

```text
1. 真实 PubMed 小任务完成；
2. Vue 发起或展示任务；
3. Agent 参与真实链路；
4. SQLite 正确持久化；
5. ServiceMatcher 工作；
6. Draft 生成；
7. Review 保存；
8. permission_check 执行；
9. test_recipient 仅少量受控测试；
10. Result Package v2 可生成和下载；
11. task_id 全链路可追溯；
12. 形成 E2E 验证报告。
```

---

## 11. Stage 40：ORCID Researcher Identity Adapter

### 11.1 进入条件

只有 Stage 39E 通过后，才建议进入 ORCID。

原因：

```text
ORCID 解决的是身份增强问题
不是当前主链路能否跑通的问题
```

### 11.2 目标

ORCID 用于辅助：

```text
Researcher Resolution
Email Association
Funding Association
Deduplication
Batch Email Safety
```

### 11.3 接入结构

严格遵守 Stage 38 Data Source Adapter 规范：

```text
ORCID Client
-> Parser
-> Service
-> Tool Adapter
-> Unified Converter
-> UnifiedResearcher
-> EvidenceRecord
```

### 11.4 禁止

```text
不能因同名就强合并
不能让 LLM 猜 ORCID
不能跳过 Evidence
Vue 不直连 ORCID
FastAPI Route 不直接写 ORCID 请求逻辑
```

### 11.5 验收

```text
Mock Tests
Raw 保存
SourceMetadata
UnifiedResearcher
ORCID Evidence
Result Package
Agent Tool
不破坏已有四源流程
```

---

## 12. Stage 41：Researcher Resolution v2

### 12.1 状态

```text
resolved
probable_match
conflicting_identity
unresolved
```

### 12.2 强证据

```text
same ORCID
same verified email
same DOI author + same institution
explicit profile link
```

### 12.3 弱证据

```text
same name
similar institution
same research topic
same country
```

仅弱证据不得自动强合并。

### 12.4 验收

```text
ORCID 强匹配可 resolve
同名不同机构不误合并
conflicting_identity 进入人工审核
Evidence 可追溯
Batch Send 使用 resolution status
至少 10 组 regression cases
```

---

## 13. Stage 42：bioRxiv / medRxiv Preprint Adapter

目标：

```text
补充最新科研方向
补充尚未正式发表成果
辅助判断近期研究趋势
```

必须明确：

```text
publication_status = preprint
```

不得与正式 peer-reviewed paper 混淆。

全部遵守 Stage 38 Adapter 规范。

---

## 14. Stage 43：Europe PMC Adapter

目标：

```text
作为 PubMed 之外的生命科学文献补充源
```

重点做好：

```text
PMID
PMCID
DOI
```

去重，避免同一论文重复计入。

---

## 15. Stage 44：Institution Public Profile Adapter

目标补充：

```text
PI Homepage
Public Email
Department
Institution
Research Direction
```

只允许：

```text
公开页面
合规访问
明确 Evidence
```

禁止：

```text
验证码绕过
登录抓取
受限后台访问
猜测邮箱格式
```

---

## 16. Stage 45：Official Scoring v1

建议权重：

```text
Funding Activity             40%
Research Direction Match     30%
Publication Recency          20%
Outsourcing Tendency         10%
```

约束：

```text
LLM 不作为唯一评分器
每个维度必须有 Evidence
missing 不伪造
scoring_version 必须保存
历史评分不静默覆盖
```

完成验收前：

```text
Scoring_Status = provisional
```

正式验收后：

```text
Scoring_Status = official
```

---

## 17. Stage 46：Production Readiness Review

检查：

```text
Security
Secrets
Rate Limit
Email Compliance
Logging
Audit
Database Migration
Backup
Recovery
Frontend
API
Background Jobs
Provider
Suppression
Idempotency
Scoring
Result Package
Monitoring
```

本阶段不代表自动上线，仍需项目方内部审批。

---

## 18. 建议目录扩展

```text
src/scholarlead_agent/
├── adapters/
│   ├── orcid/
│   ├── preprints/
│   ├── europe_pmc/
│   └── institution_profile/
│
├── services/
│   ├── researcher_resolution_service.py
│   └── service_matcher.py
│
├── email/
│   ├── quota.py
│   ├── idempotency.py
│   ├── suppression.py
│   └── eligibility.py
│
└── validation/
    ├── e2e.py
    └── service_match_benchmark.py
```

配置：

```text
data/config/
├── company_services.xlsx
├── company_services.csv
├── sender_profile.json
└── scoring_config.json
```

实际新增目录前，应先检查当前仓库是否已有等价模块，不要重复拆分。

---

## 19. 统一约束

### Agent

```text
保持一个 AgentRunner
不新建第二套 Loop
Vue 通过 FastAPI 调 Agent
ToolCall 必须对应 ToolResult
Agent 不直接持有 SMTP 密钥
Agent 不执行无人审核发送
Conversation 不替代业务数据库
```

### LLM

```text
不猜邮箱
不猜基金
不猜 ORCID
不猜机构事实
不创造公司业务
不决定高风险身份合并
不绕过 Permission
邮件必须基于 Evidence + matched_service
```

### Email

```text
默认禁止真实批量发送
approved 才能进入 send boundary
verified email 必须有 Evidence
必须 Idempotency
必须 Suppression
必须 Do Not Contact
必须 Quota
必须 normalized email dedup
crash 后不得盲目重发
SMTP accepted 不等于 delivered
```

### Data Source

```text
新数据源必须遵守 Stage 38
Raw 必须保存
SourceMetadata 必须保存
Unified Converter 必须存在
Evidence 必须生成
Mock 测试通过后才能注册 Tool
外部源不能直接在 Vue / FastAPI Route 中访问
```

### Frontend / API

```text
Vue 只调用 FastAPI
FastAPI 调 Application / Service
不复制 PubMed / Agent / Email 核心逻辑
Secrets 仅后端
Streamlit 保留为内部调试入口
Vue Agent Chat 必须使用 conversation_id
```

---

## 20. 当前优先级结论

当前最应该做的是：

```text
Stage 39A-lite
-> Stage 39B
-> Stage 39C-1
-> Stage 39C-2
-> Stage 39D
-> Stage 39E
```

暂缓：

```text
ORCID
Europe PMC
bioRxiv / medRxiv
Institution Profile
Official Scoring
Production Deployment
```

原因：

```text
当前不是缺功能点，
而是需要把现有主链路做成一个稳定、可演示、可追踪、风险可控的业务闭环。
```

---

## 21. 文档维护规则

每完成一个阶段，必须更新：

```text
docs/current_project_status.md
docs/feature_acceptance_matrix.md
```

如果用户可见行为变化，还需要更新：

```text
README.md
README_cn.md
```

阶段实施完成后，应新增对应阶段记录，例如：

```text
docs/stage39a_project_audit.md
docs/stage39b_vue_agent_connection.md
docs/stage39c1_email_basic_safety.md
docs/stage39c2_email_advanced_safety.md
docs/stage39d_service_catalog_validation.md
docs/stage39e_e2e_validation_report.md
```
