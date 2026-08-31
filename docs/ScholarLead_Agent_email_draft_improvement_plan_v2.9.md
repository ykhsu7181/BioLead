# ScholarLead Agent / BioLead 邮件草稿生成专项改进计划（v2.9 修订版）

> 执行状态：Current Specialized Next Plan
>
> 本文档是当前邮件草稿生成链路的下一步实施依据。它使用独立编号 `Email-E1` 至 `Email-E8`，不替代 `docs/ScholarLead_Agent_next_plan_v2.8.md` 的 Stage 39-46 主线编号。
>
> 当前优先顺序：先执行 `Stage 39A-lite / Email-E1`。Email-E1 是 Stage 39A-lite 中的邮件专项审计工作包；完成后，根据审计结果进入 Email-E2，不自动提前实现后续阶段。

版本：v2.9-email-draft-revised  
日期：2026-08-28  
项目：ScholarLead Agent / BioLead  
当前代码基线：Stage 38  
专项目标：在不改变现有 Review、Permission 和受控发送边界的前提下，把邮件草稿从“业务服务推荐型”升级为“基于论文证据和真实发件方能力的 Academic Cold Email”。

---

## 1. 文档定位与边界

当前项目已经具备：

```text
PubMed Lead
-> ServiceMatcher
-> SenderProfile
-> EmailDraftInput
-> EmailDraftService / LLM
-> Human Review
-> Permission Check
-> Controlled Send
```

本专项新增的重点是“能力匹配与草稿质量”，而不是新建第二套邮件系统：

```text
Paper Evidence
-> CapabilityMatcher
-> Candidate Capabilities
-> Academic Cold Email Draft
-> Draft Quality Validator
-> Existing Human Review / Permission / Controlled Send
```

本专项不做：

- 不新增 Agent 可直接调用的 `send_email` 工具。
- 不取消人工确认后的发送边界。
- 不猜测邮箱、论文结论、基金、作者身份、机构事实或发件方能力。
- 不要求全文抓取，不把出版社页面抓取作为第一版依赖。
- 不重写或删除现有 `ServiceMatcher`、`SenderProfile`、Review、Permission、Batch Send、Result Package 或 SMTP 实现。

## 2. 当前问题与目标架构

现有 `matched_service` 适合回答“论文与公司哪项业务相关”，但不等同于邮件中能够真实表达的科研能力：

```text
ServiceMatcher       -> 内部业务归类
CapabilityMatcher    -> 邮件中的科研相关性表达
```

两者并存，互不替代：

```text
                         Paper Evidence
                              |
              +---------------+---------------+
              |                               |
              v                               v
      ServiceMatcher                    CapabilityMatcher
              |                               |
              v                               v
      matched_service                 candidate_capabilities
              |                               |
              +---------------+---------------+
                              |
                              v
                       EmailDraftInput v2
                              |
                              v
                 Academic Cold Email + Quality Report
```

最终草稿应能解释：

1. 为什么联系该研究者；
2. 邮件第一段具体引用了论文中的什么信息；
3. 发件方为什么与该研究方向存在真实科研交集；
4. 邮件中的能力声明来自哪一项已配置能力；
5. 为什么该邮件不是产品列表、报价或合作项目推销。

## 3. 自动化原则与人工边界

本专项以降低草稿环节人工操作为目标。Capability Match 不作为人工审核 Gate；人工审核集中保留在既有的真实发送前流程。

```text
4-6 项能力 -> matched       -> 自动生成草稿
1-3 项能力 -> partial_match -> 自动生成草稿，只使用实际匹配能力
0 项能力   -> no_match      -> paper_only 自动生成草稿
```

规则：

- 4-6 项是推荐目标，不是硬性门槛。
- 1-3 项时不得为了凑数量添加无关能力。
- 0 项时使用 `paper_only`：只根据论文证据和固定的通用 scientific interest 写作；不得写具体 sender capability。
- `capability_match_status` 是可追溯记录和最终审核参考，不阻止正常草稿生成。
- 草稿依然默认 `review_pending`；真实发送仍须通过既有 Human Review、Permission、额度、去重、日志等规则。

## 4. 第一版邮件证据范围

第一版输入只依赖已结构化、可追溯的论文信息：

```text
Title
PubMed Abstract
Keywords / MeSH
Available metadata
```

约束：

- 没有全文时仍正常生成草稿。
- 不得让 LLM 猜测未提供的 Introduction、Results、Conclusion 或作者观点。
- Introduction 最后一段、结论、人工阅读摘要、合规获得的全文信息可作为 optional enhancement evidence；使用时必须标明来源类型和来源标识。
- 第一版不自动抓取出版社全文页面。

## 5. 邮件目标格式

邮件采用克制的三段式 Academic Cold Email，总长度建议 130-160 个英文单词。

### 5.1 Subject

优先：

```text
Academic exchange on [specific scientific topic]
```

降级：

```text
Academic exchange on your recent research
```

避免：

```text
Potential academic collaboration
Exploring collaboration
Our service for your project
```

### 5.2 Paragraph 1: Paper Observation

建议 60-70 词。必须基于标题、摘要、关键词或可用元数据，包含至少一个具体研究对象、方法、发现或科学问题；不能只写泛化称赞。

### 5.3 Paragraph 2: Sender Capability and Scientific Interest

输入为 0-6 项已匹配能力。

4-6 项时：
优先压缩为 2-3 个 capability clusters。

1-3 项时：
只自然表达实际匹配到的能力，不要求形成 2-3 个 clusters。

0 项时：
使用 paper_only。

发件人开场风格由固定 `SenderProfile` 明确配置。当前业务决定采用 `I lead ...` 时，只有在该固定发件人确实领导对应团队、且配置中明确授权时才允许使用。模型不得自行把机构能力改写为个人经历。

`paper_only` 时，本段只能使用固定 SenderProfile 中已批准的通用 scientific interest；不能出现任何未匹配的具体技术、平台、服务或团队能力。

### 5.4 Paragraph 3: Academic Exchange

建议 20-30 词。保留克制的交流入口，例如愿意交流研究思路或保持联系；不首次要求 Zoom、样本、项目合作、采购、报价或会议。

### 5.5 Greeting and Closing

称呼按以下确定性规则生成：

```text
有明确 Professor 证据 -> Dear Professor [Surname],
有明确 Dr. 证据        -> Dear Dr. [Surname],
职称或姓氏不确定        -> Dear [Full Name],
```

复杂姓名不自动转人工审核；姓名为空则不生成草稿。结尾使用固定 SenderProfile 中已配置的姓名、职位、机构和签名。

## 6. Sender Capability Catalog

`sender_capabilities.json` 是内部可配置的发件方科研能力目录，不等同于公司业务目录。

当前第一版最低字段：

```text
profile_version
capability_id
capability_name
category
description
positive_keywords
synonyms
research_fields
scientific_questions
methods
enabled
```

推荐策略字段：

```json
{
  "target_candidate_count": 4,
  "max_candidate_count": 6,
  "min_candidate_count": 0,
  "allow_fewer_when_evidence_is_insufficient": true,
  "zero_match_strategy": "paper_only",
  "llm_may_create_new_capabilities": false
}
```

当前不强制在每一项 capability 中加入完整 Evidence Governance 字段，以保持配置简洁；但必须：

- 保留 `profile_version`；
- 保留历史版本文件，不能静默覆盖；
- 保留现有 `source_policy`；
- 在扩大真实批量发送前，再评估是否补充 capability 级证据来源、审核状态、负责人和更新时间。

## 7. CapabilityMatcher v1

### 7.1 输入

```text
paper_title
abstract
keywords
matched_keywords
research_direction
organism
```

research_direction 为 optional；
若使用，必须来源于 Paper Evidence / paper metadata，
不得由 matched_service 或 company service 推导。

第一版不依赖全文。

### 7.2 输出

```text
capability_match_id
lead_id
items[]
  capability_id
  capability_name
  match_score
  match_reason
  matched_terms
status
profile_version
matcher_version
created_at
```

### 7.3 匹配规则

- v1 使用确定性、可解释的标题、摘要、关键词、同义词和可选负向关键词匹配。
- LLM 不决定能力匹配结果，不创建 capability，不提高或降低匹配分数。
- LLM 只能将已经选中的能力组织为自然语言。
- 匹配结果按分数排序并限制在最多 6 项。
- 证据不足时允许少于 4 项；没有可靠匹配时返回 `no_match`。
- 不能因论文热度、Lead Score、国家、机构或邮箱状态提高能力匹配分。

### 7.4 状态

```text
matched       4-6 项可靠匹配
partial_match 1-3 项可靠匹配
no_match      0 项可靠匹配，走 paper_only
```

状态不阻止草稿生成，也不新增 capability 阶段的人工审核节点。

## 8. EmailDraftInput v2

现有 `matched_service` 字段保留，继续供内部业务匹配、导出和其他流程使用。新字段建议为：

```text
capability_match_id
candidate_capabilities
capability_match_status
capability_profile_version
capability_matcher_version
paper_evidence_summary
paper_evidence_source_refs
sender_intro_style
email_prompt_version
```

规则：

- Academic Email 不再以 `matched_service` 为硬依赖。
- 无 Service Match、有 Capability Match 时仍可生成草稿。
- 无 Capability Match 时走 `paper_only`，仍可生成草稿。
- 旧 ServiceMatcher、批量草稿和 Result Package 不得因接口扩展失效。
- 新字段应采用可选、向后兼容方式逐步接入。

## 9. Academic Cold Email Prompt v2

System Prompt 必须明确：

```text
只使用输入 Evidence。
不得编造论文内容、基金、实验结果、客户需求、机构、邮箱或能力。
不得把 candidate capabilities 逐条罗列成产品清单。
不得使用销售话术、报价、样本请求、采购请求、会议邀请或项目合作提案。
不得声称已经发送或将自动发送邮件。
输出严格 JSON：subject、body。
```

Prompt 要求：

- 第一段有具体 paper observation；
- 第二段只使用已匹配 capability 或 paper_only 允许的通用 interest；
- 第三段只邀请学术交流；
- `I lead`、机构名称、职位、签名只来自 SenderProfile；
- 保存 `email_prompt_version`。

## 10. Draft Quality Validator

质量检查以自动检查和 warning 为主，不把普通 warning 变成额外人工节点。


fail 只用于结构性或事实性严重问题，例如：

- empty_draft
- invalid_json
- missing_subject_or_body
- unsupported_capability_claim
- paper_only_contains_specific_capability_claim
- completely_missing_paper_grounding

而：
word_count slightly outside target
generic praise detected
collaboration keyword detected
sales keyword detected
paragraph count slightly different

默认warning

```text
pass    -> 正常继续
warning -> 记录问题，正常继续
fail    -> 自动重新生成一次
```

第二次仍然 `fail` 时：

```text
quality_status = quality_failed
停止自动重试
保留草稿、质量报告和失败原因
不调用发送 Provider
```

建议检查项：

- 英文单词数：推荐 130-160；
- 三段结构；
- Subject 是否具体；
- 第一段是否有论文证据；
- 正文 capability 是否都能映射到 candidate capabilities；
- paper_only 草稿是否误写具体能力；
- 是否只有泛化赞美；
- 是否出现明显销售、报价、样本、采购、强制会议或合作提案；
- 是否含未授权的个人/机构声明；
- JSON、subject、body 是否完整。

`sales`、`collaboration` 等词仅是检测信号，不能单独判定 `fail`。自动重生成最多一次，且重生成继续只能使用同一份 Evidence 和 Capability Match。

## 11. Draft Version 与轻量快照

每个 Draft 至少保存：

```text
capability_ids
capability_match_id
capability_profile_version
matcher_version
prompt_version
draft_version
```

`match_score`、`matched_terms`、`match_reason` 等详细信息保存在 CapabilityMatch 记录中，通过 `capability_match_id` 关联。不要在每个草稿中复制完整 Sender Capability Catalog、完整 Prompt 或完整 JSON。

历史 Capability Catalog、Prompt、Matcher 版本必须保留，旧 Draft 不得因新版本上线而被静默改写。

## 12. Email-E1 至 Email-E8 实施计划

### Email-E1：邮件链路审计与测试基线

目标：确认现有 `EmailDraftInput`、`EmailDraft`、`EmailDraftService`、SenderProfile、ServiceMatcher、Batch Draft、Review、Result Package、FastAPI 和 Vue 的真实实现与测试覆盖，不立即重构。

输出：

```text
docs/email_e1_draft_chain_audit.md
```

验收：全量 pytest 通过；明确需要扩展的接口、数据库、API、Vue 页面和回归测试；不新增业务功能。

### Email-E2：Sender Capability Catalog 接入

目标：将已确认的 `sender_capabilities.json` 放入项目配置目录，增加 schema 校验和版本读取，不新增复杂 Capability Evidence Governance。

验收：重复 ID、缺少必填字段、无效策略、disabled capability 均可检测；历史版本可保留；不含密钥。

### Email-E3：CapabilityMatcher v1

目标：实现确定性能力匹配和 `matched` / `partial_match` / `no_match` 状态。

验收：4-6、1-3、0 项三种结果均可测试；不访问真实网络；不使用 LLM 决定匹配。

### Email-E4：EmailDraftInput v2 与草稿自动化分流

目标：把 CapabilityMatch 接入草稿输入，保留旧 Service 字段；实现 `paper_only` 自动草稿输入。

验收：Service Match 缺失不阻塞草稿；0 项能力不编造具体 capability；旧接口和批量草稿回归通过。

### Email-E5：Academic Cold Email Prompt v2

目标：按三段式和固定 SenderProfile 生成克制的英文草稿。

验收：模型输出只使用输入 Evidence；称呼 fallback 正确；`I lead` 只在 SenderProfile 授权时出现；输出 JSON 可解析。

### Email-E6：Draft Quality Validator

目标：生成可导出的 Quality Report，支持 warning、失败后一次自动重生成和二次失败停止。

验收：普通 warning 不阻塞；重复失败不无限调用模型；质量失败不进入 Provider 调用路径。

### Email-E7：Batch Draft v2 与 Reviewer Workspace

目标：批量自动生成草稿并在现有审核界面显示论文摘要片段、能力匹配、质量报告、版本和 warnings。

验收：不新增 capability 人工审核步骤；最终发送审核仍保留；草稿编辑、重生成和历史版本不覆盖。

### Email-E8：质量 Benchmark 与真实 E2E 验收

目标：用至少 20 篇人工标注论文对比旧 Prompt 与 Prompt v2。

验收：输出自动指标、人工评分、失败案例和 E2E 报告；未完成 Benchmark 前不扩大真实批量发送。

## 13. 数据库、API、前端与导出

数据库采用增量迁移，不破坏已有 `email_drafts`、`email_reviews`、`email_send_logs`。建议新增 `capability_matches`、`capability_match_items` 和 `email_draft_quality`，或在现有模型中以等价、可审计的方式扩展。

Result Package 建议新增：

```text
capability_matches.csv
email_draft_quality.csv
```

Vue / API 只展示和调用后端的结构化结果。浏览器不得接触 SMTP、模型密钥、Capability Catalog 完整内部配置或 Provider 凭据。

最终审核页应至少展示：

```text
收件人
论文标题和摘要片段
Capability Match 状态与已选能力
Draft Subject / Body
Quality Status / Warnings
Draft Version / Prompt Version
既有发送权限状态
```

## 14. 测试矩阵

所有新增测试不得访问真实网络，也不得调用真实模型或真实 SMTP。

```text
Catalog: schema、版本、重复 ID、disabled capability、策略字段
Matcher: 4-6、1-3、0 项、同义词、负向词、排序、最大 6 项
Draft input: Service Match 有/无、Capability Match 有/无、paper_only
Prompt: 三段结构、证据约束、称呼、I lead 授权、JSON 解析
Quality: pass、warning、fail、只重生一次、二次失败停止
Batch: 多条 lead、版本保留、Quality Report、既有 Review / Permission 回归
Export: capability match、quality report、旧 Result Package 回归
API / Vue: 仅经 FastAPI 调用，不暴露密钥
```

每个实施阶段先运行相关测试；影响共享邮件链路时再运行：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

## 15. 与 v2.8 主线的关系

本专项不改变 Stage 39-46 的总体方向。推荐顺序为：

```text
Stage 39A-lite（包含 Email-E1 邮件链路审计）
-> Email-E2
-> Email-E3
-> Email-E4
-> Email-E5
-> Email-E6
-> Email-E7
-> Email-E8
-> Stage 39C-1 / Stage 39C-2 的邮件安全增强
-> Stage 39D / Stage 39E
```

Email-E1 可以作为当前下一步的只读审计；其余阶段按验收结果逐步实施，不能因为本计划存在而跳过现有发送安全边界。

## 16. 总体验收目标

完成 Email-E8 后，系统应能做到：

1. 基于 Title、Abstract、Keywords/MeSH、metadata 自动生成邮件草稿；
2. 自动选择最多 6 项真实能力，证据不足时允许 1-3 项或 paper_only；
3. 不编造具体 sender capability、论文事实、邮箱或身份；
4. 草稿是克制的 Academic Cold Email，而不是业务产品清单或合作提案；
5. 草稿质量问题可自动记录并最多重生成一次；
6. 历史草稿、匹配、Prompt 和 Catalog 版本可追溯；
7. 人工操作集中在最终审核、许可和真实发送，不增加正常匹配环节的人为阻塞；
8. 既有 Review、Permission、限额、幂等、日志和 Controlled Send 安全边界不被削弱。
