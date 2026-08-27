# ScholarLead Agent：多数据源 Agent 扩展实施方案（v2.3）

版本：v2.3  
状态：阶段 20A～20H 后续开发计划  
日期：2026-08-21

## 1. 文档定位

本文件用于指导 ScholarLead Agent 在 PubMed 第一轮和 PubMed Agent 化完成后的后续开发。

当前项目已经从“PubMed 单源确定性链路”进入“多数据源 Agent 扩展”阶段。后续开发仍然遵守：

- 每次只执行一个阶段；
- 先读现有源码和测试；
- 不重写已经稳定通过测试的 PubMed 主链路；
- 测试默认不访问真实网络；
- 不把不确定信息说成事实；
- 不猜测邮箱、基金、通讯作者、机构或客户需求；
- 不让 LLM 直接发送邮件；
- 不把 Prompt 当成权限系统。

## 2. 当前真实项目状态

### 2.1 已完成

阶段 1～19 已完成 PubMed 第一轮主链路：

- PubMed ESearch / EFetch；
- raw 原始响应保存；
- PubMed XML 解析；
- paper 去重；
- affiliation 邮箱提取；
- Lead 生成；
- Lead 去重；
- 国家和机构基础识别；
- 关键词匹配；
- PubMed 单源临时评分；
- papers / leads JSON 和 CSV 导出；
- Run Report；
- CLI 串联；
- Streamlit 轻量展示。

阶段 20A～20H 已完成 PubMed Agent 化基础能力：

- PubMed Service；
- `search_pubmed` Tool；
- ToolRegistry；
- Agent Loop；
- OpenAI-compatible / DeepSeek 类模型适配器；
- Agent 自然语言入口；
- Streamlit Agent 测试入口；
- `generate_email_draft` 邮件草稿 Tool；
- 英文邮件草稿最小版；
- AI usage / Token 调用记录；
- Agent 与 email draft 模块级使用记录区分。

当前核心链路：

```text
用户自然语言
-> Agent Loop
-> ToolRegistry
-> search_pubmed
-> PubMed Service
-> PubMed 主链路
-> Papers / Leads / Run Report
-> Agent 最终回答
```

邮件草稿链路：

```text
Lead 详情
-> generate_email_draft
-> EmailDraftService
-> Model Adapter
-> 英文草稿
-> 人工查看 / 编辑
```

AI 使用记录：

```text
ModelClient
-> UsageTrackingModelClient
-> data/processed/ai_usage/*.jsonl
```

### 2.2 当前未完成

以下能力尚未完成，不能在对外说明中说已经完成：

- Crossref 正式数据源；
- OpenAlex 与当前 Agent / ToolRegistry 的正式整合；
- NIH RePORTER / NSF 基金源；
- ORCID 作者身份归并；
- 多数据源统一 Paper / Researcher / Organization / Funding / Evidence 模型；
- 多源 Lead 归并；
- 正式四维评分；
- 邮件审核审批流；
- 真实邮件发送；
- 数据库；
- 后台管理；
- 完整生产级客户管理平台。

## 3. 总体后续方向

后续目标是从 PubMed 单源 Agent 升级为多数据源科研客户发现 Agent。

统一建设原则：

```text
官方 API / 合规数据源
-> Client
-> Raw 保存
-> Parser / Normalizer
-> Service
-> Tool
-> ToolRegistry
-> Agent 调度
-> UI / 导出 / 报告
```

新增数据源时不要直接把第三方 API JSON 暴露给 Agent。必须先保存 raw，再清洗成项目内部结构。

## 4. 后续阶段总览

建议后续阶段如下：

```text
阶段21A：Crossref 数据源接入
阶段21B：多源统一数据模型最小版
阶段21C：OpenAlex 正式接入 Agent 架构
阶段21D：NIH RePORTER 基金数据源接入
阶段21E：Researcher / Organization / Evidence 归并
阶段21F：正式四维评分最小版
阶段21G：多数据源 Agent 调度
阶段22：Streamlit 前端升级
阶段23：邮件审核与发送权限设计
阶段24：数据库与产品化基础
阶段25：真实邮件发送最小闭环
```

其中当前下一步是：

```text
阶段21A：Crossref 数据源接入
```

不要在 21A 同时做 OpenAlex、基金、数据库、邮件发送或正式评分。

---

# 5. 阶段21A：Crossref 数据源接入

## 5.1 目标

接入 Crossref 作为 DOI 和出版元数据补充源。

第一版 Crossref 只做数据源能力，不直接生成客户 Lead，不做评分，不做邮件。

Crossref 主要补充：

- DOI；
- 标题；
- 作者；
- 期刊 / container title；
- 出版日期；
- 出版社；
- reference count；
- funder 信息如果 API 明确返回；
- Crossref source URL。

## 5.2 不做范围

阶段 21A 不做：

- PubMed 主链路重写；
- OpenAlex 正式整合；
- NIH / NSF 基金源；
- ORCID；
- Researcher 归并；
- Lead 合并；
- 正式四维评分；
- 邮件草稿增强；
- 真实邮件发送；
- 数据库；
- Agent Planner。

## 5.3 建议新增文件

按当前项目结构，建议新增：

```text
src/scholarlead_agent/crossref_models.py
src/scholarlead_agent/crossref_client.py
src/scholarlead_agent/crossref_parser.py
src/scholarlead_agent/services/crossref_service.py
src/scholarlead_agent/tools/crossref_tool.py
tests/test_crossref_models.py
tests/test_crossref_client.py
tests/test_crossref_parser.py
tests/test_crossref_service.py
tests/test_crossref_tool.py
docs/pubmed_stage21a_crossref.md
```

不要新建和当前风格不一致的大型目录，除非后续统一重构数据源架构。

## 5.4 输入参数

第一版支持两类输入：

```text
doi
title
max_results
```

规则：

- DOI 查询优先；
- DOI 为空时允许 title 查询；
- `doi` 和 `title` 至少提供一个；
- `max_results` 第一版建议最大限制为 20；
- DOI 标准化：去掉 `https://doi.org/` 前缀、trim、小写；
- 不允许空查询。

## 5.5 HTTP 要求

Crossref Client 要求：

- 使用官方公开 API；
- 设置清晰 User-Agent；
- timeout 30 秒；
- 429 和 5xx 最多重试 3 次；
- 不在测试中访问真实网络；
- API 错误不能删除已有 raw / processed 数据；
- 错误必须能被 Service / Tool 结构化返回。

## 5.6 Raw 保存

原始响应保存到：

```text
data/raw/crossref/
```

建议文件：

```text
crossref_{query_or_doi}_{timestamp}_works.json
crossref_{query_or_doi}_{timestamp}_request_meta.json
```

raw 是第三方 API 的原始 JSON 响应，不是清洗后的数据。

## 5.7 Processed 输出

清洗结果保存到：

```text
data/processed/crossref/
```

建议输出：

```text
crossref_works_{query_or_doi}_{timestamp}.json
crossref_works_{query_or_doi}_{timestamp}.csv
crossref_run_report_{query_or_doi}_{timestamp}.json
```

## 5.8 CrossrefWork 字段

第一版 `CrossrefWork` 建议字段：

```text
source = crossref
crossref_id
doi
title
abstract
journal
publisher
publication_date
publication_year
authors
funder_names
reference_count
is_referenced_by_count
source_url
raw_record_path
```

说明：

- `abstract` 可能为空；
- funder 只能使用 Crossref 返回的明确 funder 字段；
- 不得把 funder 名称推断成“有活跃基金”；
- 不得把 Crossref 作者直接合并到 PubMed Lead。

## 5.9 Parser / Normalizer 要求

Crossref Parser 负责：

- 解析 DOI；
- 解析标题；
- 解析作者；
- 解析期刊；
- 解析出版日期；
- 解析 publisher；
- 解析 funder；
- 生成 source_url；
- 处理空字段；
- 保留 raw_record_path。

日期处理：

- 优先使用 published-print；
- 其次 published-online；
- 再其次 created / deposited；
- 无法可靠判断时保留空值，不猜。

## 5.10 去重规则

Crossref work 去重：

```text
DOI -> title + publication_year + first_author
```

DOI 存在时优先 DOI。

DOI 不存在时，只做弱去重，不做跨数据源合并。

## 5.11 Service 职责

`CrossrefService` 负责：

- 接收已验证参数；
- 调用 Crossref Client；
- 保存 raw；
- 调用 parser；
- 去重；
- 保存 processed JSON / CSV；
- 生成 run report；
- 返回结构化结果。

Service 不依赖：

- Agent；
- Streamlit；
- LLM；
- 邮件；
- 数据库。

## 5.12 Tool 职责

新增：

```text
search_crossref
```

Tool 输入：

```text
doi
title
max_results
```

Tool 输出：

```text
source
task_id
status
work_count
works
raw_files
processed_files
run_report_path
errors
```

Tool 要求：

- 返回结构化 `ToolResult`；
- 不返回完整 raw JSON 给模型；
- 不发送邮件；
- 不生成 Lead；
- 不做评分。

## 5.13 ToolRegistry 接入

阶段 21A 可以把 `search_crossref` 注册到默认 ToolRegistry。

但 Agent Prompt 只需说明 Crossref 适合 DOI / 出版元数据补充，不要让 Agent 把 Crossref 当成邮箱或基金主来源。

Agent Loop 本身不得出现：

```text
if tool_name == "search_crossref"
```

## 5.14 测试策略

新增测试必须覆盖：

- DOI 标准化；
- DOI 查询参数；
- title 查询参数；
- 空查询报错；
- `max_results` 限制；
- 200 成功响应；
- 空结果；
- 429 / 5xx 重试；
- 4xx 错误；
- timeout；
- malformed JSON；
- raw 保存；
- processed JSON / CSV 保存；
- DOI 去重；
- Tool 参数校验；
- Tool 结构化返回；
- Tool 失败返回；
- 默认 ToolRegistry 包含 `search_crossref`；
- 全量 pytest 不破坏 PubMed / Agent / Email / AI usage。

测试中必须 mock HTTP，不允许真实访问 Crossref。

## 5.15 阶段 21A 验收

满足以下条件才算完成：

- Crossref DOI 查询可用；
- Crossref title 查询可用；
- raw 数据已保存；
- processed JSON / CSV 已保存；
- run report 已保存；
- `search_crossref` Tool 可被 ToolRegistry 调用；
- Agent Loop 未写死 Crossref；
- 不生成 Lead；
- 不评分；
- 不发邮件；
- 全量 pytest 通过；
- 新增阶段文档说明已完成内容和限制。

---

# 6. 阶段21B：多源统一数据模型最小版

## 6.1 目标

在 PubMed、Crossref、OpenAlex、Funding 后续接入前，建立最小统一数据模型，减少后续返工。

第一版只做模型和转换，不强行替换 PubMed 已稳定导出。

## 6.2 建议模型

建议新增：

```text
UnifiedPaper
UnifiedResearcher
UnifiedOrganization
UnifiedFunding
UnifiedContact
EvidenceRecord
```

其中最关键的是：

```text
EvidenceRecord
```

因为后续评分、邮件、报告都必须说明依据来自哪里。

## 6.3 EvidenceRecord 建议字段

```text
source_name
source_type
source_id
source_url
retrieved_at
field_name
field_value
confidence
raw_record_path
note
```

## 6.4 21B 不做范围

不做：

- 大规模迁移旧 PubMed 数据；
- 数据库；
- 正式合并算法；
- 正式评分；
- UI 大改。

## 6.5 验收

- PubMed Lead 可转换出基础 Evidence；
- Crossref Work 可转换出基础 UnifiedPaper；
- OpenAlex 旧模块可映射到 UnifiedPaper 草案；
- 不破坏原有导出；
- 全量 pytest 通过。

---

# 7. 阶段21C：OpenAlex 正式接入 Agent 架构

## 7.1 目标

当前项目已有 OpenAlex 早期代码。阶段 21C 不是从零开发，而是把已有 OpenAlex 能力整理为正式数据源模块，并接入 Service / Tool / ToolRegistry。

## 7.2 主要用途

OpenAlex 用于补充：

- 作者画像；
- 机构关系；
- 概念 / 研究方向；
- 引用数量；
- DOI 补全；
- OpenAlex Work ID；
- Authorship / institution 信息。

## 7.3 建议工作

- 复查 `openalex_client.py` 和 `works.py`；
- 保留已有测试；
- 增加 OpenAlex Service；
- 增加 `search_openalex` Tool；
- 统一 raw / processed 输出目录；
- 补充 EvidenceRecord 映射；
- 避免重复实现已存在逻辑。

## 7.4 验收

- `search_openalex` 可返回结构化 works；
- abstract_inverted_index 仍能正确还原；
- DOI 标准化仍正确；
- raw / processed 保存；
- ToolRegistry 可注册；
- 全量 pytest 通过。

---

# 8. 阶段21D：NIH RePORTER 基金数据源接入

## 8.1 目标

接入 NIH RePORTER，补充美国 NIH 项目资助信息，用于后续资金活跃度评分。

## 8.2 第一版输入

```text
pi_name
institution
keyword
from_year
to_year
max_results
```

## 8.3 输出字段

```text
grant_id
agency
project_title
pi_name
institution
fiscal_year
project_start
project_end
amount
source_url
raw_record_path
```

## 8.4 注意事项

- NIH 只覆盖 NIH 相关项目，不代表全部基金；
- 不能因为有论文就推断有基金；
- 不能因为名字相似就自动合并 PI；
- 基金归属必须保留 evidence；
- 不在 21D 做正式四维评分。

## 8.5 验收

- mock HTTP 下可完成搜索；
- raw / processed 保存；
- Tool 结构化返回；
- 失败不删除已有数据；
- 全量 pytest 通过。

---

# 9. 阶段21E：Researcher / Organization / Evidence 归并

## 9.1 目标

从“每篇论文生成 Lead”升级到“研究人员实体”。

新的关系：

```text
Paper
-> Author
-> Researcher
-> Organization
-> Contact
-> Funding
-> Lead
```

## 9.2 归并原则

禁止只按姓名合并。

强匹配信号：

- ORCID；
- 已验证邮箱；
- 明确个人主页；
- OpenAlex Author ID；
- NIH PI ID 如果可用。

弱匹配信号：

- 姓名；
- 机构；
- 论文重合；
- 国家；
- 研究方向。

归并状态：

```text
merged
probable_match
manual_review_required
distinct
```

## 9.3 验收

- 同邮箱研究者可合并；
- 只有姓名相同不会自动合并；
- 合并依据可追溯；
- 冲突记录进入人工审核；
- PubMed 原有 Lead 导出不被破坏。

---

# 10. 阶段21F：正式四维评分最小版

## 10.1 目标

从 PubMed 单源临时评分升级为正式四维评分。

默认权重：

```text
资金活跃度 40%
研究方向匹配 30%
发表时效 20%
外包倾向 10%
```

## 10.2 要求

- 权重集中配置；
- 每个分数必须保存依据；
- LLM 可以解释，不可作为唯一数值计算器；
- 基金缺失时不能用 PubMed 信息硬推基金分；
- 外包倾向如果没有证据，应标记待确认。

## 10.3 验收

- 每个 Lead / Researcher 有四维分；
- 每个维度有 evidence；
- 缺失数据明确说明；
- 优先级 high / medium / low 可配置；
- 全量 pytest 通过。

---

# 11. 阶段21G：多数据源 Agent 调度

## 11.1 目标

Agent 根据任务选择合适工具：

```text
search_pubmed
search_crossref
search_openalex
search_funding
```

## 11.2 要求

- Agent Loop 不写死工具；
- ToolRegistry 负责工具暴露；
- Agent Prompt 说明各工具边界；
- 工具失败时返回结构化错误；
- Agent 能解释使用了哪些数据源。

## 11.3 验收

- Fake Model 下可测试多工具调用；
- 真实模型 smoke test 可人工执行；
- Tool 调用记录可查看；
- 不破坏单源 PubMed 任务。

---

# 12. 阶段22：Streamlit 前端升级

## 12.1 目标

当前已有 Streamlit 轻量页面。阶段 22 是升级现有页面，不是从零新增。

## 12.2 建议展示

- Agent 执行步骤；
- Tool 调用；
- 数据来源；
- Papers；
- Researchers；
- Leads；
- Funding；
- 评分依据；
- 邮件草稿；
- AI 使用情况。

## 12.3 验收

- 用户能从一个页面完成小范围真实验证；
- 能看出每条 Lead 的来源；
- 能下载结果；
- 不出现真实发送按钮，除非后续权限阶段已完成。

---

# 13. 阶段23：邮件审核与发送权限设计

## 13.1 目标

增强邮件草稿到人工审核流程。

本阶段重点是审核和权限设计，不急于真实发送。

## 13.2 建议拆分

```text
阶段23A：邮件草稿审核状态
阶段23B：发送权限策略 PermissionPolicy
阶段23C：发送审计记录设计
```

## 13.3 必须规则

真实发送必须满足：

```text
generate draft
-> human review
-> optional edit
-> explicit approval
-> permission check
-> quota check
-> invoke send
-> record status
```

LLM 不允许直接调用发送。

## 13.4 发送前硬条件

未来真实发送前至少需要：

- verified email；
- 人工批准；
- 发送账号配置；
- 额度检查；
- 审计记录；
- 失败重试和退订/合规策略；
- 不把缺失邮箱或不确定邮箱用于发送。

---

# 14. 阶段24：数据库与产品化基础

## 14.1 目标

引入最小数据库，用于任务、实体、邮件、日志、Token 的长期保存。

## 14.2 建议表

第一版建议包含：

```text
tasks
papers
researchers
organizations
contacts
funding_records
leads
evidence_records
email_drafts
email_reviews
ai_usage
tool_calls
run_reports
```

## 14.3 原则

- 不一次性做复杂后台；
- 先保证数据能落库和查询；
- 保留文件导出能力；
- 数据库不替代 raw 文件保存；
- migration 要有测试。

---

# 15. 阶段25：真实邮件发送最小闭环

## 15.1 前置条件

只有满足以下条件后才进入真实发送：

- 邮件审核状态已完成；
- PermissionPolicy 已完成；
- 数据库审计已完成；
- 发件账号由甲方确认；
- 发送额度和失败处理已定义；
- 法务/合规口径已确认。

## 15.2 验收

- 只能发送 approved 草稿；
- 只能发送 verified email；
- 每次发送有审计记录；
- 失败有状态；
- 不允许批量无人审核自动发送。

---

# 16. 统一测试要求

每个阶段至少运行：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

数据源测试必须 mock HTTP。

LLM 测试默认使用 Fake Model。

真实 API 或真实模型只作为人工 smoke test，不能作为 pytest 的必要条件。

---

# 17. 统一安全要求

- 不提交 `.env`；
- 不记录 API Key；
- 不把用户粘贴的密钥写入日志；
- raw 数据先保存；
- 不猜测邮箱；
- 不猜测基金；
- 不按姓名强行合并；
- 不把 PubMed 临时评分说成正式评分；
- 不让 Prompt 替代权限系统。

---

# 18. 当前下一步：阶段21A 执行提示

下一次开发建议明确要求：

```text
请根据 docs/pubmed_first_round_implementation_plan_v2.3.md
只执行阶段21A：Crossref 数据源接入。
开始前先阅读当前 PubMed / Agent / ToolRegistry / OpenAlex 相关源码和测试。
不要执行 21B。
不要接入 OpenAlex、基金、数据库或邮件发送。
测试中不得访问真实网络。
完成后运行全量 pytest。
```

阶段 21A 完成后，再根据实际代码结果补充：

```text
docs/pubmed_stage21a_crossref.md
```
