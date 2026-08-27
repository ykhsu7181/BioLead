# ScholarLead Agent 下一步开发计划（v2.7 修正版）

版本：v2.7-revised  
日期：2026-08-26  
项目：ScholarLead Agent  
依据：`pubmed_first_round_implementation_plan_v2.5.md`、`ScholarLead_Agent_next_plan_v2.6.md`、当前阶段 29 后项目状态  
用途：作为阶段 30 以后新的开发依据

---

## 1. 文档定位

本文件是在 v2.6 基础上的修正版，并已合并 `ScholarLead_Agent_v2.7_revision_requirements.md` 中的修改意见。

v2.6 的总体方向是合理的，但结合当前项目实际和最新需求，需要调整后续阶段顺序：

1. 先不要一次性做完整复杂的多轮 Agent；
2. 优先补齐“公司业务范围匹配”和“邮件草稿自动补全”；
3. 再做统一结果包、后台任务和批量发送；
4. 批量邮件必须受控，不允许 Agent 无审核直接群发。
5. 后续匹配、评分、发送任务必须具备版本、状态和证据追溯。

本文件从现在开始替代：

```text
v2.5 中原阶段 30～34
v2.6 中原阶段 30～36
```

后续每次只执行一个阶段。

---

## 2. 当前项目基线

当前项目已经完成到阶段 29，已有能力包括：

```text
关键词 / 自然语言输入
-> Agent Loop
-> ToolRegistry
-> PubMed / Crossref / OpenAlex / NIH RePORTER
-> Papers / Leads / Researchers / Organizations / Funding / Evidence
-> 客户详情与 Evidence 展示
-> 邮件草稿生成
-> 人工审核
-> PermissionPolicy
-> SMTP 测试发送入口
-> SQLite 基础
-> Streamlit 前端
-> JSON / CSV / Run Report
```

当前 Agent 已有 Tool：

```text
search_pubmed
search_crossref
search_openalex
search_funding
generate_email_draft
```

当前已经验证：

```text
1. PubMed 小范围真实检索可以运行；
2. 可提取 PubMed affiliation 中公开邮箱；
3. 可生成 Lead / Papers 文件；
4. 可生成英文邮件草稿；
5. 可进行人工审核；
6. 可通过 SMTP 发送单封测试邮件；
7. 阶段 29 已增强客户详情和 Evidence 展示；
8. pytest 回归通过。
```

当前主要缺口：

```text
1. 邮件草稿仍依赖人工填写 target_service_type / sender 信息；
2. 公司业务范围还没有结构化配置；
3. Agent 还不能根据论文摘要自动匹配公司业务；
4. 多轮对话只具备基础能力，不能稳定引用上一轮结果；
5. 还没有统一结果包；
6. 几百条 Lead 的批量草稿、批量审核、批量发送还没有实现；
7. 批量发送所需 quota / idempotency / suppression / job queue 尚未完整实现。
```

---

## 3. 参考项目使用原则

### 3.1 learn-agent

`ryzqi/learn-agent` 可以作为 Agent 架构学习参考。

适合参考：

```text
Agent Loop
ToolRegistry
Permission
Hooks
Context Compaction
Memory
Dynamic Prompt
Recovery
Task DAG
Background Jobs
```

在 ScholarLead 中的对应关系：

```text
learn-agent                      ScholarLead Agent
---------------------------------------------------------
Agent Loop                   -> 现有 AgentRunner
ToolRegistry                 -> 现有 ToolRegistry
Permission                   -> 邮件发送 / 配置 / 高风险动作
Hooks                        -> tool_calls / audit / ai_usage
Context Compaction           -> 大量论文、基金、Lead 结果压缩
Memory                       -> 会话偏好，不替代客户数据库
Dynamic Prompt               -> 按任务加载公司业务和上下文
Recovery                     -> API timeout / 429 / fallback
Task DAG                     -> Search -> Match -> Draft -> Review -> Send
Background Jobs              -> 批量草稿 / 批量发送 / 结果包导出
```

禁止：

```text
1. 机械翻译 TypeScript 代码；
2. 新建第二套 Agent Loop；
3. 让 Prompt 替代 Permission 和业务规则；
4. 一次性照搬完整复杂 Harness。
```

### 3.2 BioMaster

`ai4nucleome/BioMaster` 可以作为流程控制和专业知识层参考。

适合参考：

```text
Hard Gate
Knowledge Layer / BioSkills
执行状态记录
Artifact 落盘
结果验证
用户只看摘要和结果
```

在 ScholarLead 中的对应关系：

```text
BioMaster Hard Gate
    ->
未 verified email 禁止发送
manual_review_required 禁止发送
draft 未 approved 禁止发送
quota 超限禁止发送
duplicate idempotency key 禁止发送
suppression / do_not_contact 禁止发送

BioSkills / Knowledge Layer
    ->
Company Service Catalog
Synonyms
Selling Points
Email Talking Points

Project Artifacts
    ->
Task Result Package
Run Report
Email Send Logs
Evidence Records
```

不建议照搬：

```text
Plan / Execute / Debug / Check 四 Agent 架构
生信 pipeline 结构
OpenCode / Bun 运行体系
```

ScholarLead 当前继续采用：

```text
1 个 AgentRunner
+
可靠 Tool
+
确定性 Service
+
必要的 Background Worker
```

---

## 4. 新阶段总览

后续阶段调整为：

```text
阶段 30：最小 Conversation / Task Context
阶段 31：Company Service Catalog 与 ServiceMatcher
阶段 32：邮件草稿自动补全与固定 SenderProfile
阶段 33：Result Package v1
阶段 34：Background Job 基础
阶段 34A：前后端 API 边界设计
阶段 34B：FastAPI 后端接口
阶段 34C：Vue 前端骨架与核心页面迁移
阶段 35：批量个性化邮件草稿
阶段 36：批量审核与受控批量发送
阶段 37：Result Package v2 与完整闭环
阶段 38：新增数据源 Adapter 规范
```

推荐依赖顺序：

```text
阶段30
  ↓
阶段31
  ↓
阶段32
  ↓
阶段33
  ↓
阶段34
  ↓
阶段34A
  ↓
阶段34B
  ↓
阶段34C
  ↓
阶段35
  ↓
阶段36
  ↓
阶段37
  ↓
阶段38
```

为什么这样调整：

```text
1. 当前最紧急需求是“根据公司业务范围自动匹配邮件内容”；
2. 完整多轮 Agent 可以逐步做，不必一开始过重；
3. 批量邮件必须先有 ServiceMatcher 和 SenderProfile；
4. Result Package 需要统一 task_id / lead_id / researcher_id；
5. 批量发送必须依赖后台任务、权限、额度、去重和黑名单；
6. 正式前端最依赖 Task / Job / Progress，因此放在阶段 34 后更稳；
7. 新增数据源统一通过 Adapter / Service / Tool / Unified Converter 接入，不影响当前主链路。
```

---

## 5. 阶段 30：最小 Conversation / Task Context

### 5.1 目标

让系统能够稳定知道“当前任务”和“上一轮结果”。

第一版不追求完整复杂多轮 Agent，只做最小可用：

```text
conversation_id
task_id
last_run_report_path
last_lead_ids
last_selected_lead_ids
recent_messages
```

### 5.2 需要新增

建议新增：

```text
src/scholarlead_agent/agent/conversation.py
src/scholarlead_agent/agent/context.py
```

可选数据库表：

```text
conversations
conversation_messages
conversation_state
```

### 5.3 使用场景

支持用户连续说：

```text
找 single-cell cancer 的 PI
只看有邮箱的
给前三个生成草稿
第二个人的证据是什么？
```

### 5.4 约束

```text
1. 不重写 AgentRunner；
2. 不重写 ToolRegistry；
3. 不破坏单轮 Agent；
4. 不把所有历史消息无限塞给 LLM；
5. 大结果只进入 Artifact / SQLite，LLM 只拿摘要和 ID。
```

### 5.5 验收

```text
1. 同一个 conversation_id 可以引用上一轮结果；
2. 新 conversation 不串历史；
3. 服务重启后可恢复基础状态；
4. pytest 使用 fake model，不访问真实模型；
5. 原有 Agent / Tool / PubMed 测试全部通过。
```

---

## 6. 阶段 31：Company Service Catalog 与 ServiceMatcher

### 6.1 目标

让系统根据论文标题、摘要、关键词和研究方向，匹配公司已有业务，而不是让 LLM 自由猜测。

这是后续邮件草稿自动化的核心。

### 6.2 数据源

第一版建议优先支持 CSV：

```text
data/config/company_services.csv
```

后续可支持 Excel：

```text
data/config/company_services.xlsx
```

建议字段：

```text
catalog_version
updated_at
service_id
service_name
service_category
description
positive_keywords
negative_keywords
synonyms
application_fields
supported_organisms
company_capability
selling_points
email_talking_points
enabled
```

示例：

```csv
service_id,service_name,positive_keywords,negative_keywords,selling_points,email_talking_points,enabled
single_cell_rna_seq,Single-cell RNA sequencing,"single-cell;scRNA-seq;tumor;cancer;immune","","single-cell profiling for cancer research","single-cell RNA sequencing can help resolve cell heterogeneity",true
spatial_transcriptomics,Spatial transcriptomics,"spatial transcriptomics;tumor microenvironment;FFPE","","spatial gene expression mapping","spatial transcriptomics can connect gene expression with tissue context",true
crispr_screening,CRISPR screening,"CRISPR;Cas9;gene editing;screening","","functional gene screening","CRISPR screening can help identify functional targets",true
```

### 6.3 ServiceMatcher

建议新增：

```text
src/scholarlead_agent/service_catalog.py
src/scholarlead_agent/service_matching.py
```

输入：

```text
paper_title
abstract
keywords
matched_keywords
research_direction
organism
```

输出：

```text
service_id
service_name
match_score
match_reason
matched_terms
evidence
status
catalog_version
matcher_version
```

状态：

```text
matched
no_match
needs_review
disabled_service
```

### 6.4 匹配规则

第一版使用确定性规则：

```text
positive_keywords 命中加分
synonyms 命中加分
application_fields 命中加分
negative_keywords 命中扣分
enabled=false 不参与匹配
```

LLM 可以用于解释，但不能创造公司不存在的业务。

每条匹配结果必须记录当时使用的 `catalog_version` 和 `matcher_version`。公司业务表或匹配规则后续变化时，历史匹配结果不能被新配置静默覆盖。

### 6.5 新 Tool

后续可注册：

```text
match_company_service
```

但第一版可以先做 Service，不急着注册 Agent Tool。

### 6.6 验收

```text
1. 公司服务从外部 CSV 加载；
2. 修改 CSV 后无需修改核心代码；
3. 至少准备 10～20 条论文摘要测试样例；
4. 输出 service_id / score / reason / evidence；
5. 没有合适服务时返回 no_match；
6. 不允许伪造公司业务；
7. 每条 Service Match 记录 catalog_version；
8. 每条 Service Match 记录 matcher_version；
9. 修改业务表后，历史匹配结果仍可追溯到原版本；
10. 不允许历史匹配结果被新配置静默覆盖；
11. pytest 不访问真实网络。
```

---

## 7. 阶段 32：邮件草稿自动补全与固定 SenderProfile

### 7.1 目标

邮件草稿生成时，不再要求用户手动填写：

```text
target_service_type
sender_name
sender_title
organization_name
```

系统应自动：

```text
论文摘要 / 标题 / 关键词
-> ServiceMatcher 匹配公司业务
-> 注入 SenderProfile
-> 生成个性化邮件草稿
```

### 7.2 SenderProfile

建议新增：

```text
data/config/sender_profile.json
```

字段：

```json
{
  "sender_name": "固定发件人姓名",
  "sender_title": "固定职位",
  "sender_organization": "固定机构 / 公司",
  "sender_email": "agent_test@yeah.net",
  "signature": "Best regards,..."
}
```

也可从 `.env` 读取：

```text
EMAIL_SENDER_NAME=
EMAIL_SENDER_TITLE=
EMAIL_SENDER_ORGANIZATION=
```

机密字段继续只放 `.env`：

```text
SMTP_PASSWORD
OPENAI_API_KEY
```

### 7.3 邮件草稿输入变化

当前：

```text
lead
target_service_type
service_context
sender_name
sender_title
organization_name
```

调整后：

```text
lead
matched_service
sender_profile
service_match_evidence
```

### 7.4 前端变化

邮件草稿区显示：

```text
选择 Lead
论文摘要 / 标题
匹配到的公司业务
匹配分数
匹配原因
固定发件人信息
生成草稿
人工审核
测试发送
```

不再让用户每次手动填发件人姓名、职位、机构。

### 7.5 验收

```text
1. 草稿自动使用 matched_service；
2. SenderProfile 自动注入；
3. 匹配不到服务时阻止自动生成或标记 needs_review；
4. 邮件内容必须能追溯到摘要 / matched_service；
5. 不同 Lead 邮件内容不同；
6. 不生成不存在的服务；
7. 原有单封测试发送流程不被破坏。
```

---

## 8. 阶段 33：Result Package v1

### 8.1 目标

把一次检索任务的结果整理成可交付文件包。

### 8.2 输出目录

建议：

```text
data/processed/result_packages/TASK_<task_id>/
```

第一版输出：

```text
TASK_<task_id>/
├── scholarlead_results.xlsx
├── customers.csv
├── papers.csv
├── funding.csv
├── evidence.csv
├── service_matches.csv
├── email_drafts.csv
└── task_summary.json
```

### 8.3 Excel Sheet

```text
Customers
Papers
Funding
Evidence
Service_Matches
Email_Drafts
Task_Summary
```

### 8.4 Customers 核心字段

```text
Researcher_ID
Lead_ID
PI_Name
Verified_Email
Email_Status
Email_Source
Institution
Country
Recent_Publication_Title
PMID
DOI
Funding_Status
Lead_Score
Priority
Scoring_Version
Scoring_Status
Recommendation_Reason
Matched_Service_ID
Matched_Service_Name
Service_Match_Score
Manual_Review_Required
Source_Links
```

### 8.5 Service_Matches 核心字段

```text
Task_ID
Researcher_ID
Lead_ID
Service_ID
Service_Name
Match_Score
Match_Status
Match_Reason
Matched_Terms
Evidence
Catalog_Version
Matcher_Version
Created_At
```

### 8.6 原则

ResultPackageService 只做：

```text
查询
关联
格式化
导出
```

禁止重新做：

```text
Lead 生成
Researcher 合并
Service Matching
评分
邮件生成
```

ResultPackageService 不允许重新执行 ServiceMatcher，只能读取已经保存的匹配结果并导出。

当前评分仍是草稿 / 临时评分，结果包必须明确标注：

```text
Scoring_Version = draft-v1
Scoring_Status = provisional
```

只有正式评分规则完成并验证后，才允许：

```text
Scoring_Status = official
```

### 8.7 验收

```text
1. Excel 可正常打开；
2. CSV 编码正确；
3. 空字段明确为空或 unknown；
4. Evidence 可追溯；
5. researcher_id / lead_id 可跨 Sheet 关联；
6. 可以从 Lead / Researcher 追溯到 Service Match；
7. 可以从 Service Match 追溯到匹配依据；
8. Service_Matches 与 Email_Drafts 可通过 Lead_ID / Researcher_ID 关联；
9. ResultPackageService 不重新执行 ServiceMatcher；
10. 所有 Lead_Score 都有 Scoring_Version；
11. 所有 Lead_Score 都有 Scoring_Status；
12. 当前阶段默认 Scoring_Status = provisional；
13. 历史评分不被后续算法静默覆盖；
14. pytest 覆盖导出逻辑。
```

---

## 9. 阶段 34：Background Job 基础

### 9.1 目标

为批量草稿、批量发送和结果包生成建立后台任务基础。

### 9.2 第一版 Job 类型

```text
BatchDraftJob
BatchSendJob
ResultPackageJob
```

### 9.3 Job 状态

```text
pending
running
completed
failed
cancelled
blocked
interrupted
recoverable
```

Job 字段：

```text
job_id
task_id
job_type
status
total_count
success_count
failed_count
blocked_count
created_at
started_at
finished_at
last_error
```

JobItem 字段：

```text
job_item_id
job_id
lead_id
status
attempt_count
error
started_at
finished_at
```

### 9.4 状态持久化与恢复边界

Job 和 JobItem 元数据必须持久化。服务重启后，历史 Job 必须可查询，但这不等于自动断点续跑。

如果数据库中存在：

```text
status = running
```

但当前没有对应 worker，应转换为：

```text
interrupted
```

或：

```text
recoverable
```

恢复规则：

```text
已 completed item -> 不重复执行
未执行 item -> 可人工 Retry / Resume
执行状态不确定 item -> needs_review / interrupted
高风险 Send Job -> 不允许无确认自动重发
```

### 9.5 第一版实现

第一版可以使用项目内 worker，不急于引入：

```text
Redis
Celery
RQ
```

后续如果任务量变大，再考虑独立队列。

### 9.6 验收

```text
1. 创建 job 后立即返回 job_id；
2. 前端可以查看进度；
3. 单个任务失败不影响整个批次；
4. 失败原因被记录；
5. 不自动无限重试；
6. Job 和 JobItem 状态持久化；
7. 服务重启后历史 Job 仍可查询；
8. 孤立 running Job 被识别为 interrupted / recoverable；
9. 已完成 Item 不重复执行；
10. 未完成 Item 可人工重新调度；
11. 高风险 Send Job 不允许无确认自动重发。
```

---

## 10. 阶段 34A：前后端 API 边界设计

### 10.1 目标

在正式开发 FastAPI 和 Vue 前，先定义 API 契约。

本阶段只做设计，不急于实现完整接口，也不修改现有核心业务逻辑。

需要明确：

```text
URL
HTTP Method
Request Schema
Response Schema
Error Schema
Pagination
Status
Authentication 预留
```

### 10.2 建议 API 范围

Conversation：

```text
POST   /api/conversations
GET    /api/conversations/{conversation_id}
POST   /api/conversations/{conversation_id}/messages
GET    /api/conversations/{conversation_id}/messages
```

Task：

```text
POST   /api/tasks
GET    /api/tasks/{task_id}
GET    /api/tasks/{task_id}/status
GET    /api/tasks/{task_id}/leads
```

Researcher / Lead：

```text
GET    /api/leads
GET    /api/leads/{lead_id}
GET    /api/researchers/{researcher_id}
GET    /api/researchers/{researcher_id}/papers
GET    /api/researchers/{researcher_id}/funding
GET    /api/researchers/{researcher_id}/evidence
```

Service Match：

```text
GET    /api/leads/{lead_id}/service-match
POST   /api/leads/{lead_id}/service-match
```

Email Draft / Review：

```text
POST   /api/email-drafts
GET    /api/email-drafts/{draft_id}
PATCH  /api/email-drafts/{draft_id}
POST   /api/email-drafts/{draft_id}/review
```

Job：

```text
POST   /api/jobs
GET    /api/jobs/{job_id}
GET    /api/jobs/{job_id}/items
POST   /api/jobs/{job_id}/retry
```

Result Package：

```text
POST   /api/result-packages
GET    /api/result-packages/{package_id}
GET    /api/result-packages/{package_id}/download
```

### 10.3 统一返回格式

成功：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "request_id": "..."
}
```

失败：

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "LEAD_NOT_FOUND",
    "message": "Lead not found"
  },
  "request_id": "..."
}
```

### 10.4 分页

客户、论文、Evidence、Job Items 不允许一次性返回全量。

建议：

```text
page
page_size
total
items
```

### 10.5 验收

```text
1. API 列表完成；
2. Request / Response Schema 明确；
3. Error Code 明确；
4. Pagination 明确；
5. Task / Lead / Draft / Job / ResultPackage 的 ID 规则明确；
6. 不修改现有核心业务逻辑；
7. 不开始实现 Vue 或 FastAPI 业务代码。
```

---

## 11. 阶段 34B：FastAPI 后端接口

### 11.1 目标

在现有 Python Service 上增加 FastAPI 外层接口。

FastAPI 只负责 API 边界和请求响应，不重新实现业务逻辑。

正确结构：

```text
FastAPI Router
-> Application / Service
-> AgentRunner / ToolRegistry / Database / Provider
```

禁止：

```text
FastAPI route 中直接写 PubMed 逻辑
FastAPI route 中直接写 OpenAlex 逻辑
FastAPI route 中直接发 SMTP
FastAPI route 中直接拼 ResultPackage
FastAPI route 中复制 Agent / Tool 逻辑
```

### 11.2 推荐目录

不要强制整体重构，可渐进增加：

```text
src/scholarlead_agent/api/
├── app.py
├── dependencies.py
├── errors.py
├── schemas/
│   ├── conversation.py
│   ├── task.py
│   ├── lead.py
│   ├── email.py
│   ├── job.py
│   └── result_package.py
└── routers/
    ├── conversations.py
    ├── tasks.py
    ├── leads.py
    ├── emails.py
    ├── jobs.py
    └── result_packages.py
```

### 11.3 过渡期入口

前后端分离过渡期允许：

```text
Streamlit -> 直接调用 Service
Vue       -> FastAPI -> Service
```

后续如果需要，再让 Streamlit 也走 API。

### 11.4 验收

```text
1. FastAPI 可启动；
2. 核心 API 有测试；
3. API 调用复用现有 Service；
4. 不复制 Agent / Tool 逻辑；
5. API 错误结构统一；
6. OpenAPI 文档可生成；
7. 原有 Streamlit 不受影响；
8. 原有 pytest 全部通过。
```

---

## 12. 阶段 34C：Vue 前端骨架与核心页面迁移

### 12.1 目标

建立正式用户界面的最小 Vue 骨架，并迁移核心业务页面。

阶段 34C 是最小可用 Vue，不是完整产品前端。

第一版只实现：

```text
1. Agent 对话页
2. Task / Job 执行进度页
3. 客户列表页
4. 客户详情页
5. 邮件草稿 / 审核页
```

后续再增加：

```text
批量邮件
发件账号
Token / AI Usage
系统配置
报告中心
销售跟进
操作日志
```

### 12.2 前端调用原则

```text
Vue
-> FastAPI
-> Service
-> AgentRunner / ToolRegistry / Database / EmailProvider
```

Vue 不允许直接调用：

```text
LLM
PubMed
OpenAlex
SMTP
SQLite
本地 .env
```

API Key、SMTP 密码等任何密钥不得下发到 Vue。

### 12.3 核心页面要求

Agent 对话页：

```text
conversation_id
消息历史
Agent 回复
当前 task_id
Tool / Job 简要状态
继续追问
```

Task / Job 页面：

```text
Task ID
Query
Status
数据源
Lead 数量
Job 状态
Result Package 状态
失败原因
```

客户列表页：

```text
国家
机构
邮箱状态
Funding 状态
Priority
Service Match
Manual Review
```

客户详情页：

```text
基本信息
Email Evidence
Papers
Funding
Evidence
Service Match
Score
Email Draft
Review
```

邮件审核页：

```text
Recipient
Matched Service
Match Reason
Draft Subject
Draft Body
SenderProfile
Approve
Reject
Needs Review
```

阶段 36 再增加批量发送操作。

### 12.4 Streamlit 后续定位

前后端分离以后，不删除 Streamlit。

建议定位：

```text
Vue
-> 正式用户界面

Streamlit
-> 开发调试
-> 内部 Demo
-> 快速验证 Agent / Tool / Provider
```

### 12.5 验收

```text
1. Vue 可调用 FastAPI；
2. 核心 5 个页面可访问；
3. Agent 多轮 conversation_id 正确传递；
4. Task / Job 状态可刷新；
5. 客户详情和 Evidence 正确展示；
6. Email Draft 可审核；
7. API Key / SMTP 密码不进入 Vue；
8. 原 Streamlit 仍可作为内部调试入口。
```

---

## 13. 阶段 35：批量个性化邮件草稿

### 10.1 目标

对检索到的、具有公开邮箱证据的 Lead 批量生成不同邮件草稿。

### 10.2 处理链

```text
Task Leads
-> 筛选 verified_email
-> ServiceMatcher
-> SenderProfile
-> generate_email_draft
-> EmailDraft
-> Review Queue
```

### 10.3 筛选规则

允许进入批量草稿：

```text
verified_email 不为空
email_status = verified
email_name_match_confidence = high
manual_review_required = false
邮箱有对应 Evidence
lead / researcher 未被 suppression
researcher_resolution_status = resolved
duplicate_candidate = false
normalized_recipient_email 在当前 task / campaign 中未重复
存在 recent_publication_title 或 abstract
```

邮箱来源必须单独记录，不允许和 email_status 混在一起：

```text
email_source
email_source_id
email_source_url
```

示例：

```text
email_status = verified
email_source = pubmed_affiliation
```

后续也可以支持：

```text
email_source = institution_homepage
email_source = author_public_profile
```

每个进入批量流程的邮箱必须有 Evidence：

```text
field_name = email
field_value = xxx@xxx.edu
source = PubMed / institution_homepage / author_public_profile / ...
confidence = high
```

禁止仅因为存在 email 字符串就进入批量邮件流程。

需要人工关注：

```text
manual_review_required = true
service_match = no_match
country = unknown
email_name_match_confidence != high
researcher_resolution_status != resolved
probable_match
conflicting_identity
duplicate_candidate
multiple_leads_same_email
multiple_researchers_same_email
```

邮箱级去重：

```text
normalized_recipient_email
```

同一个 `normalized_recipient_email` 在同一 task / campaign 中默认只能对应一个 active draft / active send。

### 10.4 批量草稿结果

示例：

```text
327 Leads
-> 281 verified emails
-> 270 service matched
-> 263 drafts generated
-> 12 needs_review
-> 6 failed
```

### 10.5 验收

```text
1. 不同 PI 邮件内容不同；
2. 邮件内容能追溯到论文摘要和 matched_service；
3. 不只是替换姓名；
4. SenderProfile 自动注入；
5. 每封邮件保存 model / generated_at / matched_service；
6. 单个客户失败不影响整个批次；
7. 批量草稿不依赖单一邮箱来源；
8. email_status 与 email_source 分离；
9. 每个进入批量流程的邮箱都有 Evidence；
10. email_name_match_confidence != high 时进入 needs_review；
11. 不允许猜测或生成邮箱；
12. 同一 researcher 不重复进入批次；
13. 同一 normalized_recipient_email 不重复进入同一批次；
14. probable_match / conflicting_identity / duplicate_candidate 不自动进入发送；
15. 测试使用 fake model。
```

---

## 14. 阶段 36：批量审核与受控批量发送

### 11.1 目标

实现：

```text
批量生成草稿
-> 人工审核
-> 批量确认
-> 受控发送
-> 日志记录
```

禁止：

```text
Agent 直接循环 SMTP 发送几百封
未审核直接发送
给 missing 邮箱发送
无限重试
绕过 quota
绕过 suppression
```

### 11.2 Hard Gate

至少包括：

```text
draft_status != approved -> blocked
verified_email missing -> blocked
manual_review_required -> blocked
EMAIL_SEND_ENABLED != true -> blocked
provider config missing -> blocked
quota exceeded -> blocked
do_not_contact -> blocked
suppression hit -> blocked
duplicate idempotency key -> blocked
sender account disabled -> blocked
researcher_resolution_status != resolved -> blocked
email_name_match_confidence != high -> blocked
duplicate_candidate = true -> blocked
same_recipient_already_in_batch = true -> blocked
same_recipient_already_contacted_in_task = true -> blocked / needs_review
```

这些必须由代码执行，不能只靠 Prompt。

### 11.3 第一版发送限制

建议第一版限制：

```text
每批最多 5～20 封，作为 smoke / controlled rollout 初始限制
每日上限可配置，默认 5 或 20
每封间隔可配置
失败不无限重试
只允许 approved draft
真实发送只做受控 smoke test
```

这些限制必须来自配置，不允许硬编码：

```text
EMAIL_BATCH_MAX_SIZE
EMAIL_DAILY_LIMIT
EMAIL_SEND_INTERVAL_SECONDS
```

最终实际限制服从：

```text
Provider 限额
EmailAccount 限额
项目配置
合规策略
Suppression Policy
```

### 14.4 Idempotency

建议：

```text
hash(draft_id + recipient_email + draft_version)
```

数据库层增加唯一约束或等效检查。

除 idempotency 外，批次还必须按 `normalized_recipient_email` 再次去重。同一个 recipient_email 在同一 task / campaign 中默认只能有一个 active send。

### 14.5 Suppression / Do Not Contact

建议新增：

```text
suppression_list
do_not_contact
```

字段：

```text
email
reason
source
created_at
```

### 14.6 状态

```text
blocked
queued
sending
accepted
failed
bounced
needs_review
```

只有 provider 明确返回投递事件时，才能使用：

```text
delivered
```

### 14.7 验收

```text
1. 支持批次确认；
2. 支持进度展示；
3. 双击不会重复发送；
4. quota 生效；
5. suppression 生效；
6. 单封失败不终止全批次；
7. 自动测试使用 Fake Provider；
8. 真实发送只做受控 smoke test；
9. 同一 researcher 不重复进入发送批次；
10. 同一 normalized_recipient_email 不重复进入同一批次；
11. probable_match 不自动发送；
12. conflicting_identity 不自动发送；
13. duplicate candidate 必须人工处理；
14. Idempotency 与身份去重同时生效；
15. 批量数量、每日额度和发送间隔来自配置。
```

---

## 15. 阶段 37：Result Package v2 与完整闭环

### 15.1 目标

将批量邮件和发送结果纳入最终交付包。

### 15.2 完整结果包

```text
TASK_<task_id>/
├── scholarlead_results.xlsx
├── customers.csv
├── papers.csv
├── funding.csv
├── evidence.csv
├── service_matches.csv
├── email_drafts.csv
├── email_reviews.csv
├── email_send_logs.csv
├── task_summary.json
└── README.txt
```

### 15.3 最终闭环

```text
用户输入目标
-> Agent 检索公开科研信息
-> 生成 Lead
-> Evidence 展示
-> 匹配公司业务
-> 生成个性化邮件草稿
-> 人工审核
-> 受控批量发送
-> 记录日志
-> 导出结果包
```

### 15.4 验收

```text
1. 可以从结果包看清每个客户为什么被推荐；
2. 可以看清每封邮件为什么这样写；
3. 可以看清哪些邮件发送成功、失败或被拦截；
4. 可以追溯数据来源；
5. 可以交给项目方验收或演示。
```

---

## 16. 阶段 38：新增数据源 Adapter 规范

### 16.1 目标

为后续接入 Europe PMC、bioRxiv、medRxiv、Semantic Scholar、ORCID、机构主页、公司内部客户表等数据源建立统一接入规范。

本阶段不是要求立即接入所有数据源，而是规定后续新增数据源不能绕过当前主链路。

新增数据源必须进入统一结构：

```text
DataSource Client
-> Parser
-> Service
-> Tool Adapter
-> Unified Converter
-> Paper / Researcher / Organization / Funding / Evidence / Lead
-> ResultPackage / API / Frontend / Email
```

### 16.2 新增数据源必须提供

每个数据源至少包含：

```text
DataSourceClient
DataSourceParser
DataSourceService
Tool Adapter
Unified Converter
Raw Storage
Processed Export
Mocked Tests
Run Report / Source Metadata
```

禁止：

```text
1. 直接在 Streamlit / Vue / FastAPI route 中访问外部数据源；
2. 跳过 raw 保存；
3. 跳过 Evidence；
4. 直接把外部字段硬塞进邮件生成；
5. 没有测试就注册 Agent Tool；
6. 用 LLM 猜测缺失邮箱、基金或身份。
```

### 16.3 统一 Source Metadata

所有数据源记录必须保留：

```text
source_name
source_record_id
source_url
raw_file_path
collected_at
parser_version
converter_version
confidence
license_or_terms_note
```

如果数据源有速率限制或使用限制，也必须记录：

```text
rate_limit_note
allowed_usage_note
```

### 16.4 统一模型转换

新增数据源必须尽量转换到当前统一模型：

```text
Paper
Researcher
Organization
Funding
Evidence
Lead
```

如果某个数据源只能提供部分信息，必须明确缺失字段：

```text
unknown
missing
needs_review
not_provided_by_source
```

不能把缺失字段伪造成确定事实。

### 16.5 数据源 Tool 规范

新增 Tool 命名建议：

```text
search_<source>
get_<source>_details
```

例如：

```text
search_europe_pmc
search_preprints
search_orcid
get_institution_profile
```

ToolResult 必须包含：

```text
success
source
data
error
raw_paths
processed_paths
run_report_path
queried_sources
```

### 16.6 测试要求

新增数据源测试必须：

```text
1. Mock HTTP；
2. 不访问真实网络；
3. 覆盖 200 / empty / 429 / 5xx / timeout；
4. 覆盖 parser；
5. 覆盖 raw 保存；
6. 覆盖 unified converter；
7. 覆盖 ToolResult；
8. 覆盖不完整字段 unknown / missing。
```

### 16.7 验收

```text
1. 新数据源不破坏现有 PubMed / Crossref / OpenAlex / NIH 流程；
2. 新数据源可以进入统一 Evidence；
3. 新数据源可以被 ResultPackage 导出；
4. 新数据源 Tool 可以被 AgentRunner 调用；
5. 新数据源不会绕过 Permission / Email Hard Gate；
6. 全量 pytest 通过。
```

---

## 17. 建议目录结构

按阶段逐步创建，不要求一次性重构。

```text
src/scholarlead_agent/
├── api/
│   ├── app.py
│   ├── dependencies.py
│   ├── errors.py
│   ├── schemas/
│   └── routers/
│
├── agent/
│   ├── conversation.py
│   ├── context.py
│   └── compaction.py
│
├── knowledge/
│   ├── service_catalog.py
│   └── sender_profile.py
│
├── services/
│   ├── service_matcher.py
│   ├── result_package_service.py
│   └── batch_email_service.py
│
├── sources/
│   ├── europe_pmc/
│   ├── preprints/
│   ├── orcid/
│   └── institution_profiles/
│
├── jobs/
│   ├── worker.py
│   ├── draft_jobs.py
│   └── send_jobs.py
│
└── email/
    ├── quota.py
    ├── idempotency.py
    └── suppression.py
```

配置文件：

```text
data/config/company_services.csv
data/config/sender_profile.json
```

导出结果：

```text
data/processed/result_packages/
```

---

## 18. 统一约束

### Agent

```text
1. 保持一个核心 AgentRunner；
2. 不新建第二套 Loop；
3. ToolRegistry 不硬编码完整业务流程；
4. tool_call 必须有 ToolResult；
5. Conversation 不替代业务数据库；
6. Memory 不替代 Researcher / Lead / Task 数据。
```

### LLM

```text
1. LLM 不作为唯一评分器；
2. LLM 不决定强身份合并；
3. LLM 不创造邮箱；
4. LLM 不创造基金；
5. LLM 不创造公司不存在的业务；
6. LLM 不绕过 Permission；
7. LLM 生成邮件时必须基于 Evidence 和 matched_service。
```

### Email

```text
1. 默认禁止真实发送；
2. 测试使用 Fake Provider；
3. 真实发送必须显式启用；
4. 不提交 .env；
5. 不记录 SMTP_PASSWORD / API Key；
6. 不允许无人审核批量发送；
7. 必须有 quota；
8. 必须有 idempotency；
9. 必须有 suppression / do_not_contact；
10. 失败不允许无限重试；
11. email_status 与 email_source 必须分离；
12. 每个批量流程邮箱必须有 Evidence；
13. 批量发送必须按 researcher_id 和 normalized_recipient_email 去重；
14. 批量数量、每日额度、发送间隔必须配置化。
```

### API / Frontend

```text
1. FastAPI 只做 API 边界，不复制 PubMed / Agent / Email / ResultPackage 业务逻辑；
2. API route 必须调用现有 Service / AgentRunner / ToolRegistry / Database；
3. Vue 只负责展示和用户操作；
4. Vue 不直接调用 LLM / PubMed / OpenAlex / SMTP / SQLite；
5. API Key、SMTP 密码等密钥不得下发到 Vue；
6. Streamlit 暂不删除，继续作为内部 Demo / 调试入口；
7. 前后端分离不能破坏现有 Streamlit 和 CLI 流程。
```

### Data

```text
1. raw 数据必须保留；
2. Evidence 必须保留来源；
3. unknown 不伪造成确定事实；
4. researcher_id / lead_id / task_id 必须稳定；
5. 导出不能重新计算核心业务逻辑；
6. 公司业务范围必须来自配置文件；
7. Service Match 必须记录 catalog_version 和 matcher_version；
8. Lead_Score 必须记录 Scoring_Version 和 Scoring_Status；
9. 当前评分默认 Scoring_Status = provisional；
10. 历史匹配和历史评分不允许被后续算法静默覆盖；
11. 新增数据源必须保留 source metadata；
12. 新增数据源必须转换到统一模型或明确 not_provided_by_source；
13. 新增数据源不得绕过 raw 保存和 Evidence。
```

---

## 19. 推荐立即执行的下一阶段

建议下一步执行：

```text
阶段 30：最小 Conversation / Task Context
```

原因：

```text
1. 后续业务匹配、结果包、批量邮件都需要 task_id；
2. 不需要一次性做完整多轮 Agent，只做最小上下文；
3. 可以保证“刚才这些客户”“前三个 Lead”等指代不混乱；
4. 不会阻塞阶段 31 的业务匹配开发。
```

阶段 30 完成后停止，不自动进入阶段 31。

前后端分离阶段已经纳入计划，但正式执行时间建议为：

```text
阶段 34 Background Job 基础完成后
阶段 35 批量个性化邮件草稿开始前
```

当前不建议立即开始 34A / 34B / 34C。

如果项目方更急于演示邮件业务匹配，也可以在确认后直接执行：

```text
阶段 31：Company Service Catalog 与 ServiceMatcher
```

但执行阶段 31 前，至少要确认当前一次任务的 `task_id / lead_id / run_report_path` 能稳定传递。

---

## 20. 下一条 Codex 建议提示词

```text
请阅读：

- docs/ScholarLead_Agent_next_plan_v2.7.md
- docs/pubmed_first_round_implementation_plan_v2.5.md

当前项目是 ScholarLead Agent，阶段 29 已完成。
现在只执行阶段 30：最小 Conversation / Task Context。

开始编码前请先检查：

1. 当前 AgentRunner / Agent Loop / ToolRegistry；
2. Streamlit Agent 入口；
3. SQLite 当前表结构；
4. run_report / processed files / lead_id 如何传递；
5. 当前 messages 是否只存在单次 run 生命周期；
6. 当前测试结构。

请先汇报：

1. 当前真实状态；
2. 计划新增或修改哪些文件；
3. Conversation / Task Context 的最小设计；
4. 如何保证现有单轮 Agent 不被破坏；
5. 测试策略。

本次不得执行阶段 31 及以后内容。
```
