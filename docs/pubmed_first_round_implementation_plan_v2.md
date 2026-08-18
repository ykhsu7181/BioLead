# ScholarLead Agent：PubMed 第一轮改进实施方案（Codex 后续开发版）

版本：v2.1  
日期：2026-08-18  
项目：ScholarLead Agent  
适用对象：Codex / 项目开发人员  
当前进度：第一轮阶段 1～9 已完成，后续从阶段 10 开始执行

---

## 1. 文档目的

本方案是在现有 `pubmed_first_round_implementation_plan.md` 基础上，结合当前实际开发进度和《海外 Agent 需求与验收标准-细化》重新整理的后续实施方案。

本方案的目标不是推翻现有 PubMed 第一轮，而是：

1. 保留已经完成并测试通过的阶段 1～9；
2. 继续完成阶段 10～19，使 PubMed 单源主链路形成稳定、可测试、可复现、可操作展示的内部第一轮闭环；
3. 从现在开始保持“Agent-ready”架构，但第一轮内仍不调用 LLM、不实现完整 Agent；
4. 第一轮完成后，立即衔接 PubMed Agent 化和 T+30 最小闭环，不等所有多数据源完成后才第一次接入 Agent；
5. 明确区分“PubMed 第一轮内部验收”和“合同 T+30 / T+45 验收”，避免把 PubMed 单源能力误认为完整交付。

---

## 2. 当前状态与边界

### 2.1 当前已经完成

当前第一轮已完成阶段 1～9，已具备或已实现：

```text
阶段 1：项目准备与边界确认
阶段 2：参数模型与 CLI 骨架
阶段 3：PubMed API Client
阶段 4：原始数据保存
阶段 5：PubMed XML 解析
阶段 6：邮箱提取与邮箱证据
阶段 7：论文去重
阶段 8：Lead 生成
阶段 9：Lead 去重与人工审核标记
```

当前主链路大致为：

```text
关键词 / 日期 / max_results
→ PubMed ESearch
→ PubMed EFetch
→ raw 保存
→ XML 解析
→ Paper 结构化
→ affiliation / email 提取
→ Paper 去重
→ Lead 生成
→ Lead 去重 / manual review 标记
```

### 2.2 第一轮仍未完成

后续还需要完成：

```text
阶段 10：国家与机构基础识别
阶段 11：关键词匹配与服务类型标记
阶段 12：PubMed 单源临时评分
阶段 13：Processed 数据导出
阶段 14：Run Report
阶段 15：端到端 CLI 串联
阶段 16：README / README_cn / .env.example 更新
阶段 17：完整测试与回归
阶段 18：轻量前端可视化展示
阶段 19：演示与第一轮验收材料
```

### 2.3 第一轮仍然明确“不做”

在阶段 10～19 完成前，Codex 不得主动加入以下能力：

- 不调用 LLM；
- 不开发完整 AI Agent；
- 不开发 Agent Loop；
- 不开发 ToolRegistry；
- 不把 PubMed 包装成 Agent Tool；
- 不接 Crossref；
- 不接 NIH RePORTER / NSF；
- 不接 ORCID；
- 不新增正式生产级 Web 平台；阶段 18 仅允许实现轻量 Streamlit 演示/操作界面；
- 不新增数据库；
- 不生成真实个性化邮件；
- 不发送真实邮件；
- 不做批量邮件发送；
- 不做正式四维评分；
- 不修改已经稳定的 OpenAlex 功能，除非回归测试证明存在兼容性问题。

第一轮的目标仍然是：

```text
关键词
→ PubMed
→ raw
→ 结构化 Paper
→ 联系方式证据
→ Lead
→ 临时评分
→ JSON / CSV
→ Run Report
```

---

## 3. 第一轮改进后的核心开发原则

从阶段 10 开始，除原有模块边界外，新增以下工程要求。

### 3.1 所有新增业务能力必须“Agent-ready”

所谓 Agent-ready，不是现在加入 Agent，而是要求核心业务能力可以被普通 Python 函数直接调用，将来可以无痛包装成 Tool。

例如：

```python
identify_country(...)
identify_institution(...)
find_matched_keywords(...)
calculate_topic_match_score(...)
score_pubmed_lead(...)
assign_priority(...)
```

必须满足：

- 可独立调用；
- 可独立测试；
- 不依赖 CLI；
- 不依赖 `input()`；
- 不依赖 LLM；
- 不把逻辑写死在 `pubmed_main.py`；
- 输入输出尽量结构化；
- 异常和缺失状态可预测。

### 3.2 `pubmed_main.py` 只负责流程编排

`pubmed_main.py` 不允许承担：

- 国家识别细节；
- 机构提取细节；
- 关键词评分细节；
- Lead 评分细节；
- CSV 字段拼装细节；
- 去重规则细节。

它只负责：

```text
parse args
→ validate
→ call client
→ save raw
→ parse
→ deduplicate papers
→ build leads
→ deduplicate leads
→ enrich country/institution
→ match keywords
→ score
→ export
→ run report
→ print summary
```

### 3.3 保持确定性逻辑优先

第一轮以下能力必须使用确定性 Python 逻辑，不得用 LLM 替代：

- 国家基础识别；
- 机构基础识别；
- 关键词命中；
- 临时评分；
- 优先级分层；
- 数据导出；
- Run Report；
- 去重与人工审核标记。

原因：第一轮需要稳定、可重复、可通过 pytest 验证。

### 3.4 所有缺失和推断必须有状态

禁止用空字符串掩盖“缺失 / 不确定 / 推断”。

应优先使用：

```text
unknown
missing
needs_review
candidate
inferred
source_data_not_provided
invalid_format
```

并保留置信度或来源字段。

### 3.5 不得把 PubMed 临时评分包装成正式四维评分

第一轮评分仍为：

```text
研究方向匹配度 50%
发表时效性 30%
邮箱可联系性 20%
```

必须保留：

```text
funding_activity_score = null
funding_activity_reason = Funding source not connected in PubMed-only first round
outsourcing_tendency_score = null
official_scoring_status = pending_multi_source_data
```

不得在变量名、README、输出说明或演示中写成“正式四维评分已完成”。

---

# 4. 阶段 10：国家与机构基础识别

## 4.1 目标

从作者 affiliation 中提取基础 institution / country 信息，同时保留原始文本和置信度，不把推断当事实。

## 4.2 建议修改文件

优先：

```text
src/scholarlead_agent/pubmed_leads.py
```

如当前模块已过大，可新增：

```text
src/scholarlead_agent/pubmed_affiliation.py
```

但不要为了形式强行拆文件；先检查当前代码结构再决定。

## 4.3 建议暴露函数

函数名允许根据当前代码风格调整，不要求完全照抄，但必须保持职责清晰，例如：

```text
normalize_affiliation_text(...)
identify_country_from_affiliation(...)
identify_institution_from_affiliation(...)
enrich_lead_affiliation(...)
```

## 4.4 第一版国家识别规则

至少支持常见写法：

```text
United States / USA / U.S.A. / US
United Kingdom / UK / England / Scotland / Wales
China / PR China / People's Republic of China
Japan
Germany
France
Canada
Australia
```

输出至少包括：

```text
country
country_confidence
country_source
raw_affiliation
institution
institution_confidence（如项目当前模型支持）
```

建议：

```text
country_confidence = high / medium / low / unknown
country_source = affiliation_text / email_domain_auxiliary / unknown
```

邮箱域名只能作为辅助信息，不能作为唯一强证据。

## 4.5 不允许

- 不调用 LLM 判断国家；
- 不从未知域名强行猜国家；
- 不删除 `raw_affiliation`；
- 不因国家识别失败导致 Lead 丢失。

## 4.6 测试

扩展：

```text
tests/test_pubmed_leads.py
```

至少覆盖：

- US 常见写法；
- UK 常见写法；
- China；
- Japan；
- 无法识别 → `unknown`；
- affiliation 为空；
- 邮箱域名只能辅助；
- 原始 affiliation 保留。

## 4.7 验收

- 常见国家可稳定识别；
- 不确定时输出 `unknown`；
- 有 `country_confidence`；
- 有 `country_source`；
- 机构/国家识别失败不会破坏 Lead；
- 全部已有测试继续通过。

---

# 5. 阶段 11：关键词匹配与服务类型标记

## 5.1 目标

使用 query、title、abstract、MeSH、keywords 等确定性信息生成匹配关键词和研究方向匹配依据，为临时评分服务。

## 5.2 文件

```text
src/scholarlead_agent/pubmed_scoring.py
```

## 5.3 建议函数

```text
normalize_keywords(...)
extract_query_terms(...)
find_matched_keywords(...)
build_topic_match_reason(...)
calculate_topic_match_score(...)
```

函数名称可按当前代码调整。

## 5.4 输入来源

匹配时至少允许使用：

```text
query
title
abstract
mesh_terms
keywords
service_type
```

## 5.5 输出

Lead 至少增加或补齐：

```text
matched_keywords
target_service_type
topic_match_score
topic_match_reason
```

## 5.6 规则要求

- 大小写不敏感；
- 去除多余空格；
- 第一轮允许简单 token / phrase 匹配；
- 对明确多词短语优先做 phrase 命中；
- 不使用 LLM 判断研究方向；
- 不把“没命中”伪装成命中；
- 如果甲方关键词层级表尚未提供，要在说明中标记“default rule / pending client keyword hierarchy”。

## 5.7 测试

```text
tests/test_pubmed_scoring.py
```

至少覆盖：

- title 命中；
- abstract 命中；
- MeSH 命中；
- keywords 命中；
- service_type 写入；
- 无命中；
- 大小写差异；
- 空摘要 / 空关键词。

## 5.8 验收

- 每条可评分 Lead 能输出 `matched_keywords`；
- 有 `topic_match_reason`；
- 结果稳定、可测试；
- 不依赖 LLM。

---

# 6. 阶段 12：PubMed 单源临时评分

## 6.1 目标

为 PubMed 第一轮 Demo 生成可重复、可解释的临时评分和优先级。

## 6.2 文件

```text
src/scholarlead_agent/pubmed_scoring.py
```

## 6.3 建议函数

```text
score_topic_match(...)
score_publication_recency(...)
score_email_contactability(...)
score_pubmed_lead(...)
assign_priority(...)
build_score_explanation(...)
```

## 6.4 固定权重

第一轮固定：

| 维度 | 权重 |
| --- | ---: |
| 研究方向匹配度 | 50% |
| 发表时效性 | 30% |
| 邮箱可联系性 | 20% |

优先级：

```text
>= 80   高
50-79   中
< 50    低
```

## 6.5 输出字段

```text
topic_match_score
publication_recency_score
email_contactability_score
lead_score
priority
score_explanation
funding_activity_score = null
funding_activity_reason = Funding source not connected in PubMed-only first round
outsourcing_tendency_score = null
official_scoring_status = pending_multi_source_data
```

## 6.6 关键要求

- 分数计算必须是普通 Python 逻辑；
- 相同输入必须得到相同分数；
- 评分规则必须通过单元测试；
- 评分解释应来自规则和证据，不调用 LLM；
- 不得把“有邮箱”当成研究方向匹配；
- 不得把 PubMed 临时评分称为合同正式四维评分。

## 6.7 测试

```text
tests/test_pubmed_scoring.py
```

至少覆盖：

- 高匹配 + 近期 + verified email → 高分；
- 弱匹配 + 较旧 + missing email → 低分；
- 80 边界；
- 50 边界；
- 权重合计正确；
- `score_explanation` 有内容；
- funding / outsourcing 占位字段正确。

---

# 7. 阶段 13：Processed 数据导出

## 7.1 目标

将 papers 和 leads 导出为稳定 JSON / CSV，字段名清晰、日期和评分格式一致、Excel 可正常打开。

## 7.2 文件

```text
src/scholarlead_agent/pubmed_storage.py
```

## 7.3 建议函数

```text
save_pubmed_papers_json(...)
save_pubmed_papers_csv(...)
save_pubmed_leads_json(...)
save_pubmed_leads_csv(...)
```

## 7.4 输出路径

```text
data/processed/pubmed/pubmed_papers_{safe_query}_{timestamp}.json
data/processed/pubmed/pubmed_papers_{safe_query}_{timestamp}.csv
data/processed/pubmed/pubmed_leads_{safe_query}_{timestamp}.json
data/processed/pubmed/pubmed_leads_{safe_query}_{timestamp}.csv
```

## 7.5 CSV 要求

- 使用 Excel 友好的 UTF-8 BOM；
- 列名清晰；
- 日期格式统一；
- 分数保持数字；
- list / nested 数据采用稳定序列化方式；
- 缺失状态保留 `missing / unknown / needs_review` 等语义；
- 不因单条数据字段缺失导致整批导出失败。

## 7.6 重点 Lead 字段

至少应覆盖：

```text
PI_Full_Name
Verified_Email
Email_Status
Email_Source_Type
Email_Source_URL
Name_Email_Match_Confidence
Institution
Country
Country_Confidence
Recent_Publication_Title
Journal
Publication_Year
PMID
DOI
Author_Role
Matched_Keywords
Target_Service_Type
Lead_Score
Priority
Score_Explanation
Data_Quality
Merge_Status
Merge_Reason
Manual_Review_Required
Funding_Activity_Reason
Official_Scoring_Status
Source_Links
```

## 7.7 测试

扩展：

```text
tests/test_pubmed_storage.py
```

至少覆盖：

- JSON 可重新读取；
- CSV 可读取；
- BOM 存在；
- 中文 / Unicode 不乱码；
- 数值字段格式；
- 缺失状态；
- 文件名 query + timestamp；
- 多条 Lead 导出。

---

# 8. 阶段 14：Run Report

## 8.1 目标

每次 PubMed 运行都生成可审计任务报告，能够定位输入、raw、processed、统计结果和错误。

## 8.2 文件

```text
src/scholarlead_agent/pubmed_storage.py
```

## 8.3 建议函数

```text
build_pubmed_run_report(...)
save_pubmed_run_report(...)
```

## 8.4 报告字段

至少：

```text
task_id
source
query
from_date
to_date
max_results
country
service_type
pmid_count
paper_count
lead_count
leads_with_verified_email_count
leads_needing_review_count
missing_email_count
unknown_country_count
raw_files
processed_files
errors
started_at
finished_at
status
scoring_mode = pubmed_single_source_temporary
```

建议额外记录：

```text
queried_sources = ["pubmed"]
funding_source_status = not_connected
agent_status = not_enabled_in_first_round
llm_status = not_used_in_first_round
```

## 8.5 失败行为

- ESearch 成功、EFetch 失败：保留 ESearch raw，并尽量生成失败 report；
- EFetch 成功、parser 失败：保留 EFetch raw；
- processed 导出部分失败：已经生成的 raw 不删除；
- errors 必须记录阶段、类型、消息；
- 禁止静默吞错。

## 8.6 测试

```text
tests/test_pubmed_storage.py
tests/test_pubmed_main.py
```

至少覆盖 success / partial failure / failed 三类。

---

# 9. 阶段 15：端到端 CLI 串联

## 9.1 目标

将阶段 1～14 形成一条稳定 CLI 主链路。

## 9.2 文件

```text
src/scholarlead_agent/pubmed_main.py
```

## 9.3 主流程

```text
parse args
→ validate inputs
→ create run context / timestamp / task_id
→ PubMed ESearch
→ save ESearch raw
→ PubMed EFetch
→ save EFetch raw
→ save request meta
→ parse papers
→ deduplicate papers
→ enrich affiliation / country / institution
→ build leads
→ deduplicate leads
→ match keywords / service type
→ score leads
→ save papers JSON / CSV
→ save leads JSON / CSV
→ save run report
→ print summary
```

## 9.4 CLI 输出

建议终端至少输出：

```text
ScholarLead Agent PubMed first-round run completed
Task ID: ...
PMIDs collected: ...
Papers parsed: ...
Leads generated: ...
Leads with verified email: ...
Leads needing review: ...
Unknown country: ...
Raw files: ...
Papers CSV: ...
Leads CSV: ...
Run report: ...
Scoring mode: PubMed single-source temporary scoring
LLM used: no
Agent enabled: no
```

## 9.5 重要约束

`pubmed_main.py` 不得重新实现：

- HTTP；
- XML parsing；
- email parsing；
- country logic；
- scoring logic；
- CSV formatting logic。

它只调用已有模块。

## 9.6 测试

```text
tests/test_pubmed_main.py
```

要求：

- 完整 mock ESearch / EFetch；
- 不访问真实网络；
- 能生成 raw / processed / report；
- 参数错误不请求 HTTP；
- 中间失败不删除已保存 raw；
- 终端摘要可验证关键统计。

---

# 10. 阶段 16：文档和配置更新

## 10.1 文件

```text
README.md
README_cn.md
.env.example
```

如存在：

```text
CHANGELOG.md
KNOWN_LIMITATIONS.md
```

可同步更新，但不要无必要新增大量文档。

## 10.2 README 必须说明

- PubMed 第一轮定位；
- 安装和环境；
- NCBI 环境变量；
- 运行命令；
- 输入参数；
- raw 输出；
- processed 输出；
- run report；
- 测试命令；
- 第一轮已实现；
- 第一轮未实现；
- 临时评分不是正式四维评分；
- 第一轮不使用 LLM；
- 第一轮不等于完整 Agent 交付；
- 第一轮不等于 T+45 / 最终验收。

## 10.3 `.env.example`

只允许占位：

```text
NCBI_TOOL=ScholarLeadAgent
NCBI_EMAIL=your.email@example.com
NCBI_API_KEY=
```

不得提交真实凭证。

---

# 11. 阶段 17：完整测试与回归

## 11.1 目标

确认 PubMed 第一轮功能稳定，同时不破坏已有 OpenAlex 能力。

## 11.2 执行

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

如项目已有 lint / format / type check，再按现有项目命令执行；不要自行引入新的工具链，除非项目已采用。

## 11.3 必须检查

- PubMed 全部测试通过；
- OpenAlex 已有测试仍通过；
- 测试不访问真实网络；
- `.env` 未提交；
- API Key / 邮箱凭证未硬编码；
- `data/raw` / `data/processed` 生成物是否符合 `.gitignore` 约定；
- README 与当前代码一致；
- 错误场景不会删除已有 raw；
- 临时评分标识正确；
- 无 LLM 调用；
- 无 Agent Loop；
- 无邮件发送。

## 11.4 建议测试覆盖矩阵

| 模块 | 关键测试 |
| --- | --- |
| models | 参数和日期边界 |
| client | ESearch / EFetch / retry / timeout |
| parser | PMID / DOI / title / abstract / author / affiliation |
| leads | email / confidence / candidate PI / dedup / review |
| affiliation | institution / country / unknown |
| scoring | keyword / recency / contactability / priority |
| storage | raw / JSON / CSV / report |
| main | mock end-to-end |
| OpenAlex | 回归 |

---

# 12. 阶段 18：轻量前端可视化展示（Streamlit）

## 12.1 目标

在 PubMed 第一轮后端主链路、导出、Run Report 和全量测试稳定后，增加一个轻量 Web 操作与展示界面，方便内部执行、人工检查和阶段演示。

本阶段定位为：

```text
PubMed 第一轮操作面板 / 演示界面
```

不是：

```text
最终生产级客户管理平台
```

因此本阶段优先保证“能操作、能看结果、能下载、能追溯”，不追求复杂视觉效果。

## 12.2 技术建议

优先使用：

```text
Streamlit
```

原因：

- 当前项目为 Python；
- 可直接复用现有 Python 业务模块；
- 第一轮主要用于内部操作和演示；
- 避免此阶段引入 Vue / React / 前后端分离等额外复杂度。

Codex 不得因为实现界面而重写 PubMed client / parser / leads / scoring / storage。

## 12.3 架构要求

前端不得复制业务逻辑。

推荐调用关系：

```text
CLI ─────────────┐
                 │
Streamlit UI ────┼──→ PubMed Service / 统一业务入口
                 │            ↓
未来 Agent Tool ─┘       现有 PubMed 模块
                              ↓
                client / parser / leads / scoring / storage
```

如果阶段 15 当前仍只有 `pubmed_main.py` 串联流程，Codex 可以做最小必要重构，提取一个可复用的业务入口，例如：

```python
run_pubmed_search(params)
```

函数名可根据现有代码风格调整，但必须满足：

- CLI 可调用；
- Streamlit UI 可调用；
- 后续 Agent Tool 可调用；
- 不依赖 `input()`；
- 返回结构化运行结果；
- 不复制业务逻辑。

如需新增模块，可优先考虑：

```text
src/scholarlead_agent/services/pubmed_service.py
```

但必须先检查现有结构，避免无必要拆分。

## 12.4 建议新增文件

优先：

```text
src/scholarlead_agent/ui/streamlit_app.py
```

或根据现有项目结构使用：

```text
streamlit_app.py
```

不要同时维护两个入口。

## 12.5 页面 / 功能范围

第一版至少包含以下区域。

### A. 项目功能概览

展示当前第一轮已具备能力：

```text
PubMed ESearch / EFetch
raw 保存
Paper 解析
邮箱证据
Lead 生成
Lead 去重
国家 / 机构识别
关键词匹配
PubMed 单源临时评分
JSON / CSV 导出
Run Report
```

同时明确展示当前未实现：

```text
Crossref
基金源
正式四维评分
LLM / Agent
个性化邮件
真实邮件发送
完整后台管理
```

### B. PubMed 检索任务创建

页面支持输入：

```text
query
from_date
to_date
max_results
country（可选）
service_type（可选）
```

点击执行后，调用现有统一业务入口，不通过 Shell 拼命令。

### C. 任务执行摘要

至少展示：

```text
PMID 数量
Paper 数量
Lead 数量
有邮箱 Lead 数量
缺失邮箱数量
任务状态
开始 / 结束时间
```

### D. Papers 列表

至少可展示：

```text
PMID
Title
Journal
Publication Year
DOI
Authors
Source URL
```

可进行基础查看、搜索或排序；不要求第一版实现复杂高级检索。

### E. Leads 列表

至少展示：

```text
PI / 通讯作者候选姓名
Verified Email / Email Status
Institution
Country
Lead Score
Priority
Data Quality
Manual Review Required
```

至少支持基础筛选：

```text
country
priority
email_status
```

### F. Lead 详情

选择一条 Lead 后至少展示：

```text
姓名
作者角色
机构 / 国家
邮箱
邮箱来源
邮箱来源链接
姓名邮箱匹配置信度
近期论文
PMID / DOI
matched_keywords
target_service_type
lead_score
priority
score_explanation
data_quality
merge_status / manual review 状态
```

### G. Run Report / 文件下载

至少能够：

```text
查看本次 Run Report 摘要
展示 raw / processed 文件路径
下载 papers CSV
下载 leads CSV
下载 JSON / Run Report（如现有输出已支持）
```

前端只展示和下载已经由 storage 层生成的结果，不再复制 CSV / JSON 序列化逻辑。

## 12.6 第一轮前端明确不做

本阶段不实现：

```text
登录 / 权限系统
复杂多用户管理
正式 CRM
销售跟进
多发件账号
真实邮件发送
Token 费用后台
AI 模型切换
正式后台配置
复杂图表大屏
生产级部署架构
Vue / React 重型前端
```

## 12.7 测试要求

- 不允许为 UI 测试访问真实 PubMed；
- 业务函数继续使用现有 mock 测试；
- 如新增 Service 层，必须为 Service 增加测试；
- UI 层至少保证关键 helper / 数据转换可以测试；
- UI 不得破坏现有 CLI；
- 完成后必须运行全量：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

## 12.8 阶段验收

阶段 18 只有满足以下条件才算完成：

- 浏览器可以打开第一轮界面；
- 页面可以填写 PubMed 检索参数；
- 页面可以触发已有 PubMed 主链路；
- 页面不复制 PubMed 业务逻辑；
- 可以看到任务执行摘要；
- 可以看到 Papers；
- 可以看到 Leads；
- 可以查看 Lead 详情；
- 可以查看邮箱证据和置信度；
- 可以查看临时评分和评分依据；
- 可以查看 Run Report；
- 可以下载现有导出文件；
- 无 LLM；
- 无 Agent Loop；
- 无真实邮件发送；
- CLI 仍能正常运行；
- 全量 pytest 通过。

---

# 13. 阶段 19：演示与第一轮内部验收

## 13.1 目标

证明 PubMed 第一轮单源数据链已经稳定完成。

## 13.2 演示命令

准备 1～3 个代表性关键词，至少包含：

```text
一个容易返回邮箱的主题
一个邮箱缺失较多的主题
一个带 country / service_type 条件的主题
```

## 13.3 演示流程

优先使用阶段 18 的 Streamlit 页面演示，并保留 CLI 作为备用和技术验证入口。

```text
打开第一轮可视化界面
→ 展示当前已实现 / 未实现功能
→ 输入关键词和参数
→ 执行 PubMed 检索任务
→ 展示任务执行摘要
→ 展示 Paper 结构化结果
→ 展示邮箱来源和置信度
→ 展示 PI / 通讯作者候选 Lead
→ 展示去重 / manual review
→ 展示国家 / 机构
→ 展示关键词命中
→ 展示 PubMed 临时评分和评分依据
→ 展示 Run Report
→ 下载 papers CSV / JSON
→ 下载 leads CSV / JSON
→ 必要时展示 raw ESearch / EFetch 文件路径或原始文件
```

## 13.4 演示与验收材料

阶段 19 至少准备以下材料：

```text
1. 第一轮演示命令 / 演示参数
2. Streamlit 启动命令
3. 1～3 组可复现演示关键词
4. 一份 papers CSV / JSON 示例
5. 一份 leads CSV / JSON 示例
6. 一份 run report JSON 示例
7. raw ESearch / EFetch 示例或路径说明
8. 完整 pytest 结果
9. 第一轮已实现功能清单
10. 第一轮未实现 / 已知限制清单
11. 与合同 T+30 / T+45 / 最终验收差距说明
```

如项目已有 `docs/`，建议将演示说明保存为：

```text
docs/pubmed_first_round_demo_and_acceptance.md
```

如没有 `docs/`，可按现有文档结构放置，不要为单一文件无必要重构项目目录。

## 13.5 第一轮内部验收检查

至少逐项确认：

- CLI 可运行；
- Streamlit 页面可运行；
- 页面与 CLI 共用业务入口；
- 代表性关键词可重复执行；
- Papers / Leads / Run Report 可查看；
- CSV / JSON 可下载或定位；
- 邮箱来源和姓名匹配置信度可解释；
- `manual_review_required` 等人工审核状态可展示；
- 临时评分有明确说明，不冒充正式四维评分；
- 无 LLM / Agent / 真实邮件发送；
- 全量 pytest 通过；
- OpenAlex 回归测试通过；
- 已知限制和合同差距说明完整。

## 13.6 第一轮演示口径

必须使用：

```text
本轮完成的是 PubMed 单源主链路内部第一轮。
已完成数据采集、raw 保存、结构化论文、邮箱证据、客户候选、基础去重、国家/机构基础识别、关键词匹配、PubMed 单源临时评分、导出和任务报告。
本轮不包含正式四维评分、多数据源补全、LLM 个性化邮件、真实邮件发送和完整 Agent 调度。
```

禁止使用：

```text
完整 Agent 已完成
正式四维评分已完成
客户身份已全部确认
邮箱已全部验证
合同中期验收已经完成
```

---

# 14. 第一轮 Definition of Done（改进版）

PubMed 第一轮只有同时满足以下条件才算完成：

1. CLI 参数校验稳定；
2. PubMed ESearch / EFetch 能通过 mock 测试；
3. raw 先保存；
4. Paper 核心字段可解析；
5. DOI 标准化；
6. 作者和 affiliation 可解析；
7. 邮箱只来自 affiliation；
8. 邮箱有来源和姓名对应置信度；
9. 无邮箱有明确缺失状态；
10. Paper 去重完成；
11. Lead 生成完成；
12. Lead 基础去重完成；
13. 弱匹配进入 manual review；
14. 国家 / 机构基础识别完成；
15. 无法判断国家时为 `unknown`；
16. 关键词和 service type 匹配完成；
17. PubMed 单源临时评分完成；
18. 正式 funding / outsourcing 分数保持空并有原因；
19. papers JSON / CSV 可导出；
20. leads JSON / CSV 可导出；
21. run report 可生成；
22. mock 端到端测试通过；
23. OpenAlex 回归测试通过；
24. README / README_cn / `.env.example` 更新；
25. 第一轮无 LLM；
26. 第一轮无 Agent Loop；
27. 第一轮无真实邮件发送；
28. 全部 pytest 通过；
29. 轻量 Streamlit 操作界面可打开；
30. UI 可以创建 PubMed 任务并展示 Papers / Leads / Run Report；
31. UI 可以下载现有导出文件；
32. UI 与 CLI 共用同一业务入口，不复制核心业务逻辑；
33. 演示流程可重复；
34. 已知限制和与完整需求差距说明清楚。

---

# 15. 与合同需求的关系

## 15.1 第一轮能够支持的需求方向

第一轮可作为以下能力的底层验证：

```text
关键词检索
PubMed 数据采集
来源追踪
论文结构化
邮箱来源证据
客户候选线索
基础去重
基础国家 / 机构
研究方向匹配初版
临时评分
JSON / CSV
任务报告
```

## 15.2 第一轮明确不能视为完成的合同能力

仍未完成：

```text
不少于 4 类核心数据源
Crossref 必选接入
基金源至少 1 项
ORCID / 预印本 / 开放文献类至少 1 项
多源客户归并
正式四维评分
正式客户列表页面和客户详情页
完整筛选排序
个性化英文邮件草稿
多语言邮件
人工审核发送
多发件账号与额度
批量邮件辅助
销售跟进
后台配置
Token / 费用管理
AI 模型切换
完整操作日志
完整稳定性验收
```

因此第一轮必须定位为：

```text
PubMed 单源内部技术闭环 / 数据链路验收
```

而不是：

```text
完整项目交付
```

---

# 16. 第一轮完成后的立即衔接（不属于阶段 10～19，需单独确认后执行）

> 本节用于防止项目在第一轮结束后直接跳到多个新数据源，而迟迟没有把 Agent 架构接入真实业务。

第一轮完成后，建议新增一个短阶段：

```text
阶段 20A：PubMed 业务入口 Service 化
阶段 20B：search_pubmed Tool
阶段 20C：Python ToolRegistry
阶段 20D：正式 Agent Loop
阶段 20E：DeepSeek / OpenAI-compatible Adapter
阶段 20F：PubMed Agent 真实任务测试
阶段 20G：个性化邮件草稿最小版（用于 T+30 主链路衔接）
阶段 20H：首次 LLM Token / 模型调用记录
```

上述阶段必须等阶段 19 完成并获得明确指令后再开发。

---

# 17. 第一轮后的 Agent 化目标架构

第一轮业务模块不重写，只在上层增加：

```text
用户自然语言
    ↓
LLM
    ↓
Agent Loop
    ↓
ToolRegistry
    ↓
search_pubmed Tool
    ↓
PubMed Service
    ↓
现有 PubMed client / parser / leads / scoring / storage
    ↓
Tool Result
    ↓
LLM
    ↓
最终回答
```

## 17.1 未来 Tool 粒度原则

不要把所有内部 helper 暴露成 Tool。

不建议：

```text
normalize_doi
is_valid_email
assign_priority
safe_filename
```

建议业务级 Tool：

```text
search_pubmed
search_crossref
search_funding
resolve_researcher
get_lead_details
generate_email_draft
```

---

# 18. 第一轮后的 T+30 衔接说明

合同 T+30 最小闭环要求接近：

```text
关键词 / 自然语言
→ 数据采集
→ 客户列表
→ 评分分级
→ 客户详情
→ 邮件草稿
→ 导出
```

PubMed 第一轮完成后，仍建议至少补：

1. 自然语言 → 结构化搜索参数；
2. `search_pubmed` Agent Tool；
3. Agent Loop；
4. 基于 Lead / paper / abstract / service_type 的个性化英文邮件草稿最小版；
5. 邮件草稿不自动发送；
6. LLM 调用记录、模型名称、Token usage 至少开始落日志；
7. 复用阶段 18 的轻量前端展示客户列表 / Lead 详情；后续正式平台形态仍按项目阶段要求扩展。

这部分不应提前混入第一轮阶段 10～19。

---

# 19. 多数据源后续建议顺序

完成 PubMed Agent 化后，再进入多数据源：

```text
1. Crossref
2. 基金源：NIH RePORTER 或 NSF
3. OpenAlex 正式纳入主链路 / ORCID（二选一先做）
4. 达到不少于 4 类核心数据源
5. 多源统一字段
6. 多源客户归并
7. 正式四维评分
8. 个性化邮件增强
9. 人工审核和发送
10. 后台配置 / Token / 日志 / 销售跟进
```

每个新数据源遵循统一方式：

```text
业务 Client / Collector
→ Parser / Normalizer
→ 测试稳定
→ Service
→ Tool
→ registry.register(...)
```

新增数据源时原则上不修改 Agent Loop。

---

# 20. Codex 每阶段统一执行规则

Codex 在阶段 10～19 每次只完成当前阶段，不得越级开发。

每次开始前：

1. 先阅读当前相关源码；
2. 先阅读对应测试；
3. 不假设不存在的函数名；
4. 尽量复用已有数据模型和 helper；
5. 不重写已经通过测试的模块；
6. 如必须调整已有接口，先说明原因和影响范围；
7. 不主动做无关重构；
8. 不引入新框架，除非现有项目明确需要；
9. 完成当前阶段后先运行对应测试；
10. 再运行全量 pytest 做回归。

每次完成后必须汇报：

```text
1. 修改了哪些文件
2. 新增了哪些函数 / 数据字段
3. 为什么这样设计
4. 是否修改已有接口
5. 运行了哪些测试
6. 测试结果
7. 当前阶段是否通过验收
8. 尚有哪些已知限制
9. 下一阶段建议，但不要自动开始下一阶段
```

---

# 21. Codex 当前立即执行任务：阶段 10

将以下内容直接作为下一次 Codex 指令：

```text
当前项目是 ScholarLead Agent。
PubMed 第一轮阶段 1～9 已完成并已有测试。

现在只完成“阶段 10：国家与机构基础识别”。
不要继续阶段 11，也不要开发 Agent / LLM / ToolRegistry。

要求：

1. 先阅读当前 pubmed_models.py、pubmed_parser.py、pubmed_leads.py
   以及 tests/test_pubmed_leads.py，确认当前字段结构和函数接口。

2. 不要重写已经工作的 PubMed client、parser、email、lead 和 dedup 逻辑。

3. 在现有结构上实现 affiliation 的基础国家和机构识别。
   如果 pubmed_leads.py 已经过大，可以新建 pubmed_affiliation.py；
   如果没必要，不要为了拆文件而拆文件。

4. 国家识别至少支持常见写法：
   - United States / USA / US
   - United Kingdom / UK / England / Scotland / Wales
   - China / PR China / People's Republic of China
   - Japan
   - Germany
   - France
   - Canada
   - Australia

5. 无法确认时：
   country = unknown
   不得乱猜。

6. 保留 raw_affiliation 原文。

7. 输出或补齐：
   - institution
   - country
   - country_confidence
   - country_source
   - raw_affiliation

8. 邮箱域名只能作为辅助证据，不能作为唯一高置信国家来源。

9. 所有核心识别逻辑必须通过普通 Python 函数暴露：
   - 可独立调用
   - 可独立测试
   - 不依赖 CLI
   - 不依赖 LLM
   - 后续可以直接包装成 Agent Tool 或 Service 内部能力

10. 不要把国家识别逻辑写进 pubmed_main.py。

11. 扩展 tests/test_pubmed_leads.py，至少覆盖：
   - US
   - UK
   - China
   - Japan
   - unknown
   - 空 affiliation
   - 原始 affiliation 保留
   - 置信度和来源字段

12. 先运行相关测试，再运行：

    .\literature_env\Scripts\python.exe -m pytest

13. 不允许真实网络访问。

14. 完成后停止，不要自动开始阶段 11。

完成后告诉我：
- 修改了哪些文件
- 新增了哪些函数
- institution / country 的识别规则
- confidence / source 的定义
- 新增了哪些测试
- pytest 结果
- 是否存在已知限制
```

---

# 22. 阶段 10 完成后的 Codex 顺序

阶段 10 通过后，依次执行：

```text
阶段 11 → 关键词匹配
阶段 12 → 临时评分
阶段 13 → JSON / CSV
阶段 14 → Run Report
阶段 15 → 端到端 CLI
阶段 16 → README / 配置
阶段 17 → 全量测试 / 回归
阶段 18 → 轻量 Streamlit 可视化展示
阶段 19 → 演示与内部验收
```

每个阶段单独下发任务，单独测试，单独验收。

不要一次让 Codex 完成阶段 10～19 全部内容。

---

# 23. 一句话总结

当前最合理的实施方式是：

```text
先把 PubMed 第一轮阶段 10～19 按确定性 Python 逻辑完成并测稳，其中阶段 18 只增加轻量可视化操作层；
从现在开始保持所有模块 Agent-ready，但第一轮不引入 LLM；
第一轮通过后立刻增加 PubMed Service → Tool → ToolRegistry → Agent Loop，
再用同一架构逐步接入 Crossref、基金源、OpenAlex / ORCID 和邮件能力。
```
