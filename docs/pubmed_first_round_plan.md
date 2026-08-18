# PubMed 单源主链路第一轮开发方案

版本：v0.4  
日期：2026-08-17  
项目名称：ScholarLead Agent

## 1. 文档目的

本文档用于明确 ScholarLead Agent 第一轮只针对 PubMed 的主链路开发方案。

第一轮目标不是完成完整海外科研客户 Agent，而是先用 PubMed 单一公开数据源跑通最小闭环，为后续接入 Crossref、OpenAlex、NIH RePORTER、NSF、ORCID、bioRxiv/medRxiv、AI 邮件和人工审核发送打基础。

本文档依据：

- 《海外Agent需求与验收标准-细化》
- 前期讨论中确认的 PubMed 单源主链路方案
- 当前仓库已有 OpenAlex 采集原型和测试结构

## 2. 第一轮定位

PubMed 第一轮定位为：

```text
PubMed 单源科研客户线索主链路 Demo
```

第一轮要证明系统可以完成：

```text
关键词输入
→ PubMed 检索
→ 原始数据保存
→ 论文数据清洗
→ 作者/机构/邮箱解析
→ PI/通讯作者候选线索生成
→ PubMed 单源临时评分
→ 邮件草稿入口预留
→ 客户线索和论文结果导出
```

与需求书 T+30 主链路演示的关系：

需求书要求演示：

```text
关键词检索
→ 数据采集
→ 客户列表
→ 评分分级
→ 客户详情
→ 邮件草稿
→ 导出
```

PubMed 第一轮对应实现：

```text
关键词检索
→ PubMed 数据采集
→ PubMed 客户候选列表
→ PubMed 临时评分分级
→ 客户候选详情数据
→ 邮件草稿字段和入口预留
→ JSON/CSV 导出
```

## 3. 第一轮实现范围

### 3.1 必须实现

- 命令行创建 PubMed 检索任务。
- 支持关键词、日期范围、最大结果数。
- 支持目标国家和目标服务类型作为可选参数。
- 调用 PubMed ESearch 获取 PMID 列表。
- 调用 PubMed EFetch 获取原始 XML。
- 保存 ESearch 原始响应和 EFetch 原始 XML。
- 解析论文核心字段。
- 从 affiliation 中提取公开邮箱。
- 标注邮箱来源链接和邮箱来源类型。
- 无邮箱时标注缺失原因。
- 生成 PI/通讯作者候选客户线索。
- 生成 PubMed 单源临时评分和高/中/低优先级。
- 输出结构化论文 JSON/CSV。
- 输出客户候选线索 JSON/CSV。
- 测试中模拟 HTTP，不访问真实网络。

### 3.2 预留但不完整实现

- 邮件草稿字段。
- 邮件草稿生成入口。
- 客户详情报告字段。
- 后续正式四维评分字段。
- 后续多数据源来源字段。

### 3.3 第一轮暂不实现

- Crossref。
- OpenAlex 增强。
- NIH RePORTER / NSF 基金采集。
- ORCID 作者身份归并。
- bioRxiv/medRxiv 预印本采集。
- Web 页面。
- SQLite 数据库。
- 完整 AI Agent 编排。
- LLM 邮件草稿真实生成。
- 真实邮件发送。
- 批量邮件发送。
- 自动猜测邮箱。

## 4. 输入参数设计

第一轮命令行参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--query` | 是 | 检索关键词，例如 `single cell RNA sequencing cancer` |
| `--from-date` | 是 | 开始日期，格式 `YYYY-MM-DD` |
| `--to-date` | 是 | 结束日期，格式 `YYYY-MM-DD` |
| `--max-results` | 是 | 最大结果数，第一轮建议限制 1 到 100 |
| `--country` | 否 | 目标国家，例如 `US`、`GB`、`JP` |
| `--service-type` | 否 | 目标服务类型，例如 `scRNA-seq`、`RNA-seq` |
| `--raw-dir` | 否 | 原始数据保存目录，默认 `data/raw/pubmed` |
| `--processed-dir` | 否 | 清洗结果保存目录，默认 `data/processed/pubmed` |

示例：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main `
  --query "single cell RNA sequencing cancer" `
  --from-date 2024-01-01 `
  --to-date 2024-12-31 `
  --max-results 100 `
  --country US `
  --service-type scRNA-seq
```

## 5. 参数校验规则

| 参数 | 校验规则 |
| --- | --- |
| `query` | 不能为空，去除首尾空格 |
| `from_date` | 必须为 `YYYY-MM-DD` |
| `to_date` | 必须为 `YYYY-MM-DD` |
| 日期范围 | `from_date` 必须早于或等于 `to_date` |
| `max_results` | 第一轮限制为 1 到 100 |
| `country` | 可为空；如提供则保留原始输入并标准化为大写 |
| `service_type` | 可为空；如提供则用于关键词匹配和导出 |

校验失败时应输出清晰错误，不发起 PubMed 请求。

## 6. PubMed 采集方案

使用 NCBI E-utilities，不做网页抓取。

采集流程：

```text
构造 PubMed 查询条件
→ ESearch 获取 PMID 列表
→ 保存 ESearch 原始响应
→ EFetch 获取 PubMed XML
→ 保存 EFetch 原始 XML
→ 解析 XML
```

建议接口：

- ESearch：`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi`
- EFetch：`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi`

ESearch 建议参数：

| 参数 | 示例 |
| --- | --- |
| `db` | `pubmed` |
| `term` | 用户 query 与日期条件组合 |
| `retmode` | `json` |
| `retmax` | `max_results` |
| `sort` | `pub date` |
| `tool` | `ScholarLeadAgent` |
| `email` | 从环境变量读取 |
| `api_key` | 如有，从环境变量读取 |

EFetch 建议参数：

| 参数 | 示例 |
| --- | --- |
| `db` | `pubmed` |
| `id` | PMID 列表，逗号分隔 |
| `retmode` | `xml` |
| `rettype` | `abstract` |
| `tool` | `ScholarLeadAgent` |
| `email` | 从环境变量读取 |
| `api_key` | 如有，从环境变量读取 |

## 7. HTTP 与稳定性要求

按照需求书中“数据源异常不应导致已有数据丢失”的原则，第一轮应实现：

- 请求超时 30 秒。
- 对 429 和 5xx 最多重试 3 次。
- 设置清晰 User-Agent。
- 读取 NCBI email、tool、api key 等配置时使用环境变量。
- 请求失败时保存错误状态和错误原因。
- 已保存的 raw 数据不得因后续清洗失败被删除。
- ESearch 成功但 EFetch 失败时，应保留 ESearch 结果和失败日志。
- EFetch 成功但清洗失败时，应保留 EFetch 原始 XML。

环境变量建议：

```text
NCBI_TOOL=ScholarLeadAgent
NCBI_EMAIL=your.email@example.com
NCBI_API_KEY=
```

`.env.example` 可以后续补充示例，但不得写真实 API key。

## 8. 原始数据保存

原始数据指 PubMed API 返回后，尚未清洗、筛选、合并、改写之前的数据。

保存目录：

```text
data/raw/pubmed/
```

建议文件：

```text
{safe_query}_{timestamp}_esearch.json
{safe_query}_{timestamp}_efetch.xml
{safe_query}_{timestamp}_request_meta.json
```

`request_meta.json` 建议记录：

```json
{
  "source": "pubmed",
  "query": "single cell RNA sequencing cancer",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31",
  "max_results": 100,
  "country": "US",
  "service_type": "scRNA-seq",
  "esearch_endpoint": "...",
  "efetch_endpoint": "...",
  "collected_at": "2026-08-17T10:00:00",
  "status": "success"
}
```

保存原则：

- 先保存原始数据，再执行清洗。
- 原始数据尽量保持源返回内容。
- 清洗规则变化后，可以基于原始数据重新处理。
- 原始数据文件名必须包含 query 和时间戳。

## 9. PubMed 字段解析

论文层字段：

| 字段 | 说明 |
| --- | --- |
| `source` | 固定为 `pubmed` |
| `pmid` | PubMed ID |
| `doi` | DOI，需标准化 |
| `title` | 论文标题 |
| `abstract` | 摘要 |
| `journal` | 期刊名称 |
| `publication_date` | 发表日期 |
| `publication_year` | 发表年份 |
| `article_types` | 文章类型 |
| `mesh_terms` | MeSH 主题词 |
| `keywords` | 关键词 |
| `authors` | 作者列表 |
| `affiliations` | 作者机构文本 |
| `emails` | affiliation 中提取的邮箱 |
| `source_url` | PubMed 页面链接 |
| `raw_record_path` | 原始 XML 文件路径 |

PubMed 链接：

```text
https://pubmed.ncbi.nlm.nih.gov/{pmid}/
```

DOI 标准化：

- 去除 `https://doi.org/` 前缀。
- 去除 `doi:` 前缀。
- 转小写。
- 去除首尾空格。

## 10. 作者和机构结构

作者结构：

```json
{
  "full_name": "John Smith",
  "last_name": "Smith",
  "fore_name": "John",
  "initials": "J",
  "author_position": 1,
  "is_last_author": false,
  "affiliations": [],
  "emails": []
}
```

机构结构第一轮不做复杂标准化，先保留：

```json
{
  "raw_affiliation": "Department of Biology, Example University, USA",
  "institution_name": "Example University",
  "country": "US",
  "country_confidence": "medium",
  "country_source": "affiliation_text"
}
```

机构解析边界：

- 第一轮保留原始 affiliation。
- 可尝试提取机构名和国家。
- 无法确定机构时标记 `unknown`。
- 不把推断结果当作确认事实。

## 11. 邮箱解析和姓名对应规则

这是第一轮的关键风险点。

邮箱只允许从 PubMed affiliation 文本中提取，不允许猜测。

必须记录：

- 邮箱。
- 邮箱格式是否有效。
- 邮箱来源类型。
- 邮箱来源链接。
- 邮箱所在 affiliation 文本。
- 邮箱对应作者姓名。
- 对应关系置信度。

邮箱结构：

```json
{
  "email": "john.smith@example.edu",
  "email_status": "verified_from_pubmed_affiliation",
  "email_source_type": "pubmed_affiliation",
  "email_source_url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
  "matched_author_name": "John Smith",
  "matched_affiliation": "Department ..., john.smith@example.edu",
  "name_email_match_confidence": "high"
}
```

姓名和邮箱对应规则：

| 场景 | 处理 |
| --- | --- |
| 邮箱在某个作者自己的 affiliation 节点中 | 可标记高置信度 |
| 多个作者共用同一 affiliation 且只有一个邮箱 | 标记中置信度或人工确认 |
| 邮箱出现在整体文本但无法对应作者 | 不自动绑定具体作者，进入人工确认 |
| 邮箱格式无效 | 标记 `invalid_format` |
| 没有邮箱 | 标记 `missing` |

无邮箱记录：

```text
email_status = missing
email_reason = source_data_not_provided
queried_sources = PubMed
```

## 12. 客户候选线索生成

第一轮不承诺识别“已确认 PI”，统一使用：

```text
PI/通讯作者候选线索
```

生成规则：

1. 有明确邮箱且可对应作者的记录，优先生成可联系客户候选。
2. 最后一作者可作为 PI 候选，但必须标记为推断。
3. 有机构但无邮箱的作者可生成无邮箱候选。
4. 无法确认是否同一人的记录不自动合并。
5. 同一 PMID 内重复邮箱去重。
6. 跨 PMID 同邮箱可初步合并为同一候选客户。

Lead 字段：

| 字段 | 说明 |
| --- | --- |
| `lead_id` | 本地生成 ID |
| `pi_full_name` | PI/通讯作者候选姓名 |
| `name_variants` | 姓名变体，第一轮可为空 |
| `verified_email` | 已验证邮箱，如有 |
| `email_status` | 邮箱状态 |
| `email_source_url` | 邮箱来源链接 |
| `email_source_type` | 邮箱来源类型 |
| `institution` | 机构 |
| `country` | 国家 |
| `country_confidence` | 国家识别置信度 |
| `recent_publication_title` | 近期论文标题 |
| `abstract` | 摘要或摘要来源 |
| `journal` | 期刊 |
| `publication_year` | 发表年份 |
| `pmid` | PMID |
| `doi` | DOI |
| `author_role` | first_author、last_author、email_author、candidate_pi |
| `matched_keywords` | 命中关键词 |
| `target_service_type` | 目标服务类型 |
| `lead_score` | PubMed 单源临时评分 |
| `priority` | 高/中/低 |
| `score_explanation` | 评分依据 |
| `data_quality` | 数据质量状态 |
| `source_links` | 数据来源链接 |

## 13. 去重与归并

第一轮做基础去重，不做复杂客户归并。

论文去重：

```text
DOI 优先
没有 DOI 时使用 PMID
```

客户候选去重：

```text
已验证邮箱相同 → 可合并
同一 PMID + 同一作者名 → 可合并
姓名相同 + 机构相同 → 生成候选，不强制合并
只有姓名相同 → 不合并
```

人工确认字段：

```text
merge_status = confirmed / candidate / needs_review / not_merged
merge_reason = email_match / same_pmid_author / same_name_institution
```

## 14. 国家识别

PubMed affiliation 是自由文本，国家识别只能辅助。

策略：

- 从 affiliation 文本匹配国家或地区。
- 使用邮箱域名作为辅助信息。
- 无法判断时标记 `unknown`。
- 保存置信度和来源。

字段：

```text
country
country_confidence
country_source
```

示例：

```text
country = US
country_confidence = medium
country_source = affiliation_text
```

## 15. 研究方向和服务类型匹配

第一轮根据以下文本做关键词命中：

- query。
- title。
- abstract。
- MeSH terms。
- keywords。
- article types。

匹配输出：

```text
matched_keywords
target_service_type
topic_match_reason
```

如果甲方提供关键词层级表，则按层级打分。未提供时，第一轮使用默认关键词匹配，不作为正式验收评分规则。

## 16. PubMed 单源临时评分

需求书正式评分是四维评分：

- 资金活跃度 40%。
- 研究方向匹配度 30%。
- 发表时效性 20%。
- 外包倾向 10%。

但 PubMed 单源无法完整判断基金活跃度和外包倾向，因此第一轮使用“PubMed 单源临时评分”，并在导出中明确标记。

临时评分：

| 维度 | 权重 | 依据 |
| --- | --- | --- |
| 研究方向匹配度 | 50% | 标题、摘要、MeSH、关键词命中 |
| 发表时效性 | 30% | 发表日期距当前时间 |
| 邮箱可联系性 | 20% | 是否有公开邮箱和来源 |

分级：

- 高优先级：`>= 80`
- 中优先级：`50-79`
- 低优先级：`< 50`

正式评分字段占位：

```text
funding_activity_score = null
funding_activity_reason = Funding source not connected in PubMed-only first round
topic_match_score = ...
publication_recency_score = ...
outsourcing_tendency_score = null
official_scoring_status = pending_multi_source_data
```

## 17. 邮件草稿与人工审核边界

需求书要求生成个性化英文邮件草稿，并且正式发送前必须人工确认。

PubMed 第一轮建议实现：

- 邮件草稿输入数据准备。
- 邮件草稿字段预留。
- 可导出邮件草稿占位字段。

第一轮不建议实现：

- LLM 真实调用。
- 真实邮件发送。
- 批量自动发送。

后续邮件流程：

```text
选中客户候选线索
→ 基于近期论文和服务类型生成英文邮件草稿
→ 人工编辑
→ 人工确认
→ 发送
→ 记录发送状态
```

邮件草稿字段：

| 字段 | 说明 |
| --- | --- |
| `email_draft_subject` | 邮件标题 |
| `email_draft_body` | 邮件正文 |
| `email_draft_language` | 语言，第一版英文 |
| `draft_status` | draft / reviewed / approved |
| `draft_generated_at` | 生成时间 |
| `model_name` | 后续 AI 模型名称 |
| `human_reviewer` | 人工审核人 |

安全边界：

- 不允许无人审核自动发送。
- 不允许自动猜邮箱后发送。
- 正式发送必须有人确认并记录状态。

## 18. 导出方案

保存目录：

```text
data/processed/pubmed/
```

输出文件：

```text
pubmed_papers_{safe_query}_{timestamp}.json
pubmed_papers_{safe_query}_{timestamp}.csv
pubmed_leads_{safe_query}_{timestamp}.json
pubmed_leads_{safe_query}_{timestamp}.csv
pubmed_run_report_{safe_query}_{timestamp}.json
```

论文 CSV 字段：

- `PMID`
- `DOI`
- `Title`
- `Abstract`
- `Journal`
- `Publication_Date`
- `Publication_Year`
- `Authors`
- `Affiliations`
- `Emails`
- `Mesh_Terms`
- `Keywords`
- `Source_URL`
- `Raw_Record_Path`

客户线索 CSV 字段：

- `PI_Full_Name`
- `Verified_Email`
- `Email_Status`
- `Email_Source`
- `Email_Source_URL`
- `Name_Email_Match_Confidence`
- `Institution`
- `Country`
- `Country_Confidence`
- `Recent_Publication_Title`
- `Abstract_or_Source_Link`
- `Journal`
- `Publication_Year`
- `PMID`
- `DOI`
- `Author_Role`
- `Matched_Keywords`
- `Target_Service_Type`
- `Lead_Score`
- `Priority`
- `Score_Explanation`
- `Data_Quality`
- `Funding_Activity_Reason`
- `Email_Draft_Status`
- `Notes`

导出要求：

- CSV 使用 UTF-8 with BOM 或 Excel 兼容编码，避免中文乱码。
- 字段名清晰。
- 日期格式统一。
- 分数为数字。
- 缺失字段必须有状态说明。

## 19. 任务报告

第一轮需要生成任务报告，便于验收和排错。

任务报告字段：

```json
{
  "task_id": "pubmed_20260817_100000",
  "source": "pubmed",
  "query": "...",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31",
  "max_results": 100,
  "pmid_count": 100,
  "paper_count": 95,
  "lead_count": 30,
  "leads_with_email_count": 12,
  "missing_email_count": 18,
  "raw_files": [],
  "processed_files": [],
  "errors": [],
  "started_at": "...",
  "finished_at": "...",
  "status": "success"
}
```

## 20. 建议模块结构

新增模块：

```text
src/scholarlead_agent/pubmed_client.py
src/scholarlead_agent/pubmed_parser.py
src/scholarlead_agent/pubmed_models.py
src/scholarlead_agent/pubmed_leads.py
src/scholarlead_agent/pubmed_scoring.py
src/scholarlead_agent/pubmed_storage.py
src/scholarlead_agent/pubmed_main.py
```

测试文件：

```text
tests/test_pubmed_client.py
tests/test_pubmed_parser.py
tests/test_pubmed_leads.py
tests/test_pubmed_scoring.py
tests/test_pubmed_storage.py
tests/test_pubmed_main.py
```

测试 fixture：

```text
tests/fixtures/pubmed_esearch_response.json
tests/fixtures/pubmed_efetch_response.xml
```

## 21. 开发顺序

建议按以下顺序开发：

1. 定义 PubMed 输入参数和校验。
2. 实现 PubMed ESearch client。
3. 实现 PubMed EFetch client。
4. 实现原始响应保存。
5. 编写 PubMed XML fixture。
6. 实现 XML 解析。
7. 实现 DOI、日期、作者名、邮箱清洗。
8. 实现邮箱来源和姓名对应置信度。
9. 实现客户候选线索生成。
10. 实现论文和客户候选去重。
11. 实现 PubMed 单源临时评分。
12. 实现 JSON/CSV 导出。
13. 实现任务报告。
14. 增加 pytest 测试。
15. 更新 README。

## 22. 测试策略

测试中不允许访问真实网络。

必须覆盖：

- 参数校验。
- ESearch 请求参数。
- EFetch 请求参数。
- User-Agent、timeout、retry。
- 429 和 5xx 重试。
- 请求失败不删除已有 raw 文件。
- PubMed XML 解析。
- 多段摘要合并。
- DOI 标准化。
- 作者姓名解析。
- affiliation 提取。
- 邮箱格式校验。
- 邮箱和作者对应关系。
- 无邮箱状态标记。
- 国家识别置信度。
- Lead 生成。
- 基础去重。
- 临时评分。
- JSON/CSV 导出。
- 任务报告生成。

## 23. 第一轮验收标准

输入一个关键词后，系统应能：

- 创建 PubMed 检索任务。
- 获取 PMID 列表。
- 获取 PubMed XML。
- 保存原始 ESearch 和 EFetch 响应。
- 输出结构化论文 JSON/CSV。
- 解析论文标题、摘要、期刊、年份、DOI、作者和机构。
- 从 affiliation 中提取公开邮箱。
- 标注邮箱来源链接和邮箱与姓名的对应关系。
- 无邮箱时标记缺失原因。
- 生成 PI/通讯作者候选线索。
- 输出客户候选线索 JSON/CSV。
- 给出 PubMed 单源临时评分和优先级。
- 输出评分依据。
- 输出任务报告。
- 测试中模拟 HTTP，不访问真实网络。

## 24. 与完整验收标准的差距

PubMed 第一轮不能作为最终完整交付。

与完整验收仍存在差距：

| 完整验收要求 | PubMed 第一轮状态 |
| --- | --- |
| 不少于 4 类核心数据源 | 只做 PubMed |
| Crossref 必选 | 未接入 |
| 基金源至少 1 项 | 未接入 |
| ORCID/预印本/开放文献至少 1 项 | 未接入 |
| 正式四维评分 | 仅临时评分 |
| 个性化 AI 邮件 | 仅预留字段 |
| 邮件人工确认发送 | 未实现 |
| 客户详情页面 | 未实现 |
| 后台配置 | 未实现 |
| Token 费用记录 | 未实现 |

因此第一轮应定位为：

```text
主链路技术验证和数据清洗验证
```

不是：

```text
最终验收版本
```

## 25. 风险与处理

| 风险 | 影响 | 处理 |
| --- | --- | --- |
| PubMed 邮箱不完整 | 可联系客户数量少 | 无邮箱标记 missing，不猜测 |
| 邮箱和作者对应不清 | 可能错配收件人 | 低置信度进入人工确认 |
| 通讯作者不明确 | PI 判断不稳定 | 使用候选线索口径 |
| affiliation 自由文本 | 机构和国家解析不稳定 | 保留原文，标注置信度 |
| PubMed 无完整基金信息 | 资金活跃度无法正式评分 | 标记基金源未接入 |
| 单源数据无法完成客户归并 | 同一 PI 可能重复 | 只做基础去重，复杂归并留到多源阶段 |
| API 限流或失败 | 任务中断 | 超时、重试、错误日志、保留已有 raw 数据 |
| CSV 中文乱码 | 验收导出失败 | 使用 Excel 兼容编码 |

## 26. 下一步衔接

PubMed 第一轮完成后，建议下一步：

1. 接入 Crossref，补 DOI 和出版元数据。
2. 接入 NIH RePORTER 或 NSF，补基金和资金活跃度。
3. 接入 ORCID，提升作者身份归并能力。
4. 接入 OpenAlex 增强或 bioRxiv/medRxiv，补开放文献和预印本。
5. 实现正式四维评分。
6. 实现个性化英文邮件草稿。
7. 实现人工审核和发送记录。
8. 实现客户列表和客户详情页面。

## 27. 总结

PubMed 单源第一轮的核心目标是：

```text
把公开论文数据转成可追溯、可导出、可初步评分的客户候选线索
```

最小闭环：

```text
关键词
→ PubMed
→ raw 保存
→ 清洗结构化
→ 邮箱证据
→ PI/通讯作者候选
→ 临时评分
→ 导出
```

该链路稳定后，再扩展多数据源、正式评分、AI 邮件和人工审核发送。

## 28. 详细执行步骤

本节把 PubMed 第一轮拆成可直接开发的步骤。建议严格按顺序完成，每完成一步就补对应测试。

### Step 1：创建 PubMed 模块文件

新增文件：

```text
src/scholarlead_agent/pubmed_models.py
src/scholarlead_agent/pubmed_client.py
src/scholarlead_agent/pubmed_parser.py
src/scholarlead_agent/pubmed_leads.py
src/scholarlead_agent/pubmed_scoring.py
src/scholarlead_agent/pubmed_storage.py
src/scholarlead_agent/pubmed_main.py
```

新增测试文件：

```text
tests/test_pubmed_models.py
tests/test_pubmed_client.py
tests/test_pubmed_parser.py
tests/test_pubmed_leads.py
tests/test_pubmed_scoring.py
tests/test_pubmed_storage.py
tests/test_pubmed_main.py
```

新增 fixture：

```text
tests/fixtures/pubmed_esearch_response.json
tests/fixtures/pubmed_efetch_response.xml
```

验收：

- 文件结构创建完成。
- 不影响现有 OpenAlex 测试。

### Step 2：定义 PubMed 输入参数模型

文件：`pubmed_models.py`

建议定义：

```text
PubMedSearchParams
PubMedPaper
PubMedAuthor
PubMedAffiliation
PubMedEmail
PubMedLead
PubMedRunReport
```

`PubMedSearchParams` 字段：

```text
query
from_date
to_date
max_results
country
service_type
raw_dir
processed_dir
```

校验函数：

```text
validate_pubmed_search_inputs(...)
```

验收：

- 空 query 报错。
- 日期格式错误报错。
- `from_date > to_date` 报错。
- `max_results < 1` 报错。
- `max_results > 100` 报错。
- country 可选，提供时转大写。

### Step 3：实现 PubMed CLI

文件：`pubmed_main.py`

命令示例：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main `
  --query "single cell RNA sequencing cancer" `
  --from-date 2024-01-01 `
  --to-date 2024-12-31 `
  --max-results 100 `
  --country US `
  --service-type scRNA-seq
```

CLI 职责：

```text
解析参数
→ 校验参数
→ 调用 PubMed client
→ 保存 raw
→ 解析 XML
→ 生成 lead
→ 评分
→ 导出
→ 输出文件路径和统计信息
```

验收：

- `--help` 正常显示。
- 参数错误时不发起 HTTP。
- CLI main 返回状态码。

### Step 4：实现 PubMed ESearch Client

文件：`pubmed_client.py`

函数建议：

```text
build_esearch_params(search_params)
fetch_pubmed_ids(search_params)
```

ESearch 参数：

```text
db=pubmed
term={query} AND {from_date}:{to_date}[dp]
retmode=json
retmax=max_results
sort=pub date
tool=ScholarLeadAgent
email=NCBI_EMAIL
api_key=NCBI_API_KEY
```

返回：

```json
{
  "pmids": ["123", "456"],
  "raw_response": {}
}
```

验收：

- 请求 URL 正确。
- 参数正确。
- timeout 为 30 秒。
- User-Agent 清晰。
- 测试中 mock HTTP，不访问真实 PubMed。

### Step 5：实现 PubMed EFetch Client

文件：`pubmed_client.py`

函数建议：

```text
build_efetch_params(pmids)
fetch_pubmed_xml(pmids)
```

EFetch 参数：

```text
db=pubmed
id=123,456
retmode=xml
rettype=abstract
tool=ScholarLeadAgent
email=NCBI_EMAIL
api_key=NCBI_API_KEY
```

返回：

```text
原始 XML 字符串
```

验收：

- 空 PMID 列表不调用 EFetch。
- PMID 正确逗号拼接。
- XML 原文完整返回。

### Step 6：实现 HTTP 重试和错误处理

文件：`pubmed_client.py`

规则：

```text
429 重试
500/502/503/504 重试
最多重试 3 次
非重试错误直接抛出
每次请求 timeout=30
```

错误结构建议：

```json
{
  "source": "pubmed",
  "step": "esearch",
  "status": "failed",
  "error_type": "HTTPError",
  "error_message": "...",
  "attempts": 4
}
```

验收：

- 429 后成功时返回结果。
- 503 后成功时返回结果。
- 超过 3 次仍失败时抛出清晰错误。
- 已保存 raw 文件不被删除。

### Step 7：保存原始响应

文件：`pubmed_storage.py`

函数建议：

```text
build_pubmed_output_paths(query, timestamp)
save_esearch_raw(raw_response, path)
save_efetch_raw(xml_text, path)
save_request_meta(meta, path)
```

文件路径：

```text
data/raw/pubmed/{safe_query}_{timestamp}_esearch.json
data/raw/pubmed/{safe_query}_{timestamp}_efetch.xml
data/raw/pubmed/{safe_query}_{timestamp}_request_meta.json
```

验收：

- 文件名包含 query 和时间戳。
- raw 文件保存于 `data/raw/pubmed`。
- 保存失败不生成部分损坏文件，建议使用临时文件再替换。
- XML 使用 UTF-8。

### Step 8：准备 PubMed XML Fixture

文件：

```text
tests/fixtures/pubmed_efetch_response.xml
```

fixture 至少包含：

- 2 篇文章。
- 1 篇有 DOI。
- 1 篇无 DOI。
- 1 篇有多段摘要。
- 1 篇有多个作者。
- 1 个作者 affiliation 中含邮箱。
- 1 个 affiliation 无邮箱。
- 1 个无效邮箱用于测试过滤。

验收：

- fixture 不依赖真实网络。
- XML 覆盖核心解析场景。

### Step 9：解析 PubMed XML 为论文对象

文件：`pubmed_parser.py`

函数建议：

```text
parse_pubmed_xml(xml_text) -> list[PubMedPaper]
parse_article(article_node) -> PubMedPaper
extract_pmid(article_node)
extract_doi(article_node)
extract_title(article_node)
extract_abstract(article_node)
extract_publication_date(article_node)
extract_journal(article_node)
extract_mesh_terms(article_node)
extract_keywords(article_node)
extract_authors(article_node)
```

解析要求：

- 多段摘要合并成一个字符串。
- DOI 标准化。
- 日期尽量输出 `YYYY-MM-DD`，无法完整时至少保留年份。
- 缺失字段不报错，标记为空或 `unknown`。

验收：

- PMID 正确。
- DOI 正确标准化。
- title 正确。
- abstract 正确合并。
- authors 数量正确。
- journal 和 publication_date 正确。

### Step 10：解析作者和 affiliation

文件：`pubmed_parser.py`

作者字段：

```text
full_name
last_name
fore_name
initials
author_position
is_first_author
is_last_author
affiliations
emails
```

规则：

- `full_name = fore_name + last_name`。
- 没有 fore_name 时使用 last_name。
- author_position 从 1 开始。
- 最后一作者 `is_last_author = true`。
- affiliation 保留原文。

验收：

- 作者顺序正确。
- 最后一作者识别正确。
- affiliation 不丢失。

### Step 11：提取邮箱并校验

文件：`pubmed_parser.py` 或 `pubmed_leads.py`

函数建议：

```text
extract_emails_from_affiliation(affiliation_text)
is_valid_email(email)
build_pubmed_email(email, author, affiliation, pmid)
```

规则：

- 只从 affiliation 文本提取。
- 邮箱转小写。
- 去除末尾标点。
- 无效邮箱标记 `invalid_format`。
- 不根据姓名或机构推测邮箱。

验收：

- 有效邮箱能提取。
- 无效邮箱不进入 `verified_email`。
- 邮箱来源 URL 为 PubMed 链接。
- 邮箱对应作者姓名正确。

### Step 12：判断邮箱与姓名对应置信度

文件：`pubmed_leads.py`

规则：

```text
high：邮箱出现在某个作者自己的 affiliation 节点中
medium：多个作者共享 affiliation，邮箱无法唯一对应
low：邮箱出现在文章整体文本中但无法绑定作者
none：无邮箱
```

验收：

- high 置信度可作为可联系 lead。
- medium/low 需要标记 `manual_review_required`。
- 不确定时不强绑定收件人。

### Step 13：识别国家和机构

文件：`pubmed_parser.py` 或 `pubmed_leads.py`

第一版策略：

- 保留 `raw_affiliation`。
- 用简单规则识别国家词，例如 `USA`、`United States`、`UK`、`China`、`Japan`。
- 邮箱域名只作为辅助。
- 无法识别时 `country=unknown`。

输出：

```text
institution
country
country_confidence
country_source
```

验收：

- 能识别常见国家。
- 不确定时不猜，标记 `unknown`。
- 保留原始 affiliation。

### Step 14：生成 PubMed Paper JSON/CSV

文件：`pubmed_storage.py`

函数建议：

```text
save_pubmed_papers_json(papers, path)
save_pubmed_papers_csv(papers, path)
```

CSV 字段：

```text
PMID
DOI
Title
Abstract
Journal
Publication_Date
Publication_Year
Authors
Affiliations
Emails
Mesh_Terms
Keywords
Source_URL
Raw_Record_Path
```

验收：

- JSON 可读。
- CSV 可用 Excel 打开。
- 中文不乱码。
- 列名清晰。

### Step 15：生成客户候选 Lead

文件：`pubmed_leads.py`

函数建议：

```text
build_leads_from_papers(papers, search_params)
build_lead_from_author(paper, author, email)
```

Lead 生成优先级：

1. 有 high 置信度邮箱的作者。
2. 有 medium 置信度邮箱的作者，但标记人工确认。
3. 最后一作者，无邮箱时作为 PI 候选。
4. 有机构但无邮箱的相关作者。

验收：

- 有邮箱作者生成可联系 lead。
- 最后一作者生成候选 lead。
- 无邮箱 lead 标记 `missing`。
- 每条 lead 有 PubMed 来源链接。

### Step 16：Lead 去重

文件：`pubmed_leads.py`

函数建议：

```text
deduplicate_pubmed_leads(leads)
```

规则：

```text
verified_email 相同 → 合并
同一 PMID + 同一作者名 → 合并
姓名相同 + 机构相同 → 标记 candidate，不强合并
只有姓名相同 → 不合并
```

验收：

- 同邮箱不重复。
- 同论文同作者不重复。
- 弱匹配不误合并。

### Step 17：关键词和服务类型匹配

文件：`pubmed_scoring.py`

函数建议：

```text
find_matched_keywords(paper, query, service_type)
calculate_topic_match_score(...)
```

匹配来源：

```text
query
title
abstract
mesh_terms
keywords
```

验收：

- query 中关键词可命中。
- title/abstract 中关键词可命中。
- 输出 `matched_keywords` 和 `topic_match_reason`。

### Step 18：计算 PubMed 单源临时评分

文件：`pubmed_scoring.py`

函数建议：

```text
score_pubmed_lead(lead)
score_topic_match(lead)
score_publication_recency(lead)
score_email_contactability(lead)
assign_priority(score)
```

临时评分：

```text
研究方向匹配度 50%
发表时效性 30%
邮箱可联系性 20%
```

优先级：

```text
>=80 高优先级
50-79 中优先级
<50 低优先级
```

验收：

- 有评分总分。
- 有优先级。
- 有 `score_explanation`。
- 明确 `funding_activity_reason = Funding source not connected in PubMed-only first round`。

### Step 19：保存 Lead JSON/CSV

文件：`pubmed_storage.py`

函数建议：

```text
save_pubmed_leads_json(leads, path)
save_pubmed_leads_csv(leads, path)
```

CSV 字段：

```text
PI_Full_Name
Verified_Email
Email_Status
Email_Source
Email_Source_URL
Name_Email_Match_Confidence
Institution
Country
Country_Confidence
Recent_Publication_Title
Abstract_or_Source_Link
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
Funding_Activity_Reason
Email_Draft_Status
Notes
```

验收：

- 字段齐全。
- 缺失邮箱有状态。
- 评分和日期格式正确。
- CSV 打开不乱码。

### Step 20：生成任务报告

文件：`pubmed_storage.py`

函数建议：

```text
build_pubmed_run_report(...)
save_pubmed_run_report(report, path)
```

报告字段：

```text
task_id
source
query
from_date
to_date
max_results
pmid_count
paper_count
lead_count
leads_with_email_count
missing_email_count
raw_files
processed_files
errors
started_at
finished_at
status
```

验收：

- 每次运行都有报告。
- 报告能定位 raw 和 processed 文件。
- 失败时记录错误原因。

### Step 21：预留邮件草稿字段

文件：`pubmed_leads.py` 或后续 `email_drafts.py`

第一轮只预留字段：

```text
email_draft_subject
email_draft_body
email_draft_language
draft_status
draft_generated_at
model_name
human_reviewer
```

默认：

```text
draft_status = not_generated
email_draft_language = en
```

验收：

- Lead 导出中有邮件草稿状态。
- 不调用 LLM。
- 不发送邮件。

### Step 22：实现端到端 CLI 串联

文件：`pubmed_main.py`

主流程：

```text
parse args
→ validate inputs
→ fetch PMIDs
→ save ESearch raw
→ fetch XML
→ save EFetch raw
→ parse papers
→ save paper outputs
→ build leads
→ score leads
→ save lead outputs
→ save run report
→ print summary
```

终端输出示例：

```text
ScholarLead Agent PubMed run completed
PMIDs collected: 100
Papers parsed: 95
Leads generated: 30
Leads with verified email: 12
Raw ESearch: data/raw/pubmed/...
Raw EFetch: data/raw/pubmed/...
Papers CSV: data/processed/pubmed/...
Leads CSV: data/processed/pubmed/...
Run report: data/processed/pubmed/...
```

验收：

- 成功时输出统计。
- 失败时错误清晰。
- 不破坏已保存文件。

### Step 23：补充 README

文件：`README.md`

新增：

- PubMed 第一轮定位。
- 安装依赖。
- 环境变量。
- 运行命令。
- 输出文件说明。
- 第一轮限制。
- 测试命令。

验收：

- 新同事按 README 可以运行。
- 明确 PubMed 第一轮不是完整交付。

### Step 24：完整测试清单

执行：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

至少新增测试：

| 测试文件 | 测试内容 |
| --- | --- |
| `test_pubmed_models.py` | 参数校验、模型转换 |
| `test_pubmed_client.py` | ESearch/EFetch 参数、重试、timeout |
| `test_pubmed_parser.py` | XML 解析、摘要、作者、DOI、邮箱 |
| `test_pubmed_leads.py` | Lead 生成、邮箱状态、去重 |
| `test_pubmed_scoring.py` | 临时评分和优先级 |
| `test_pubmed_storage.py` | raw/processed/report 保存 |
| `test_pubmed_main.py` | CLI 端到端 mock 流程 |

验收：

- 所有测试通过。
- 测试不访问真实网络。
- 旧 OpenAlex 测试不受影响。

### Step 25：第一轮演示脚本

演示步骤：

1. 准备一个关键词，例如 `single cell RNA sequencing cancer`。
2. 运行 PubMed CLI。
3. 展示 raw 文件。
4. 展示 papers CSV。
5. 展示 leads CSV。
6. 解释邮箱来源链接和邮箱状态。
7. 解释临时评分。
8. 展示 run report。
9. 说明 PubMed 单源与完整验收的差距。

验收话术：

```text
本轮只验证 PubMed 单源主链路，已完成关键词检索、数据采集、原始数据保存、结构化清洗、邮箱证据、客户候选线索、临时评分和导出。
正式四维评分、基金信息、客户归并和邮件发送将在多源阶段完成。
```

## 29. 建议开发排期

如果只做 PubMed 第一轮主链路，建议按 5 到 7 个工作日安排。

### Day 1：参数、模型和 CLI 骨架

目标：

- 定义 PubMed 输入参数。
- 定义论文、作者、邮箱、客户候选、任务报告数据模型。
- 建立 PubMed CLI 骨架。

交付：

```text
pubmed_models.py
pubmed_main.py 初版
tests/test_pubmed_models.py
tests/test_pubmed_main.py 初版
```

完成标准：

- `--help` 可运行。
- 参数校验测试通过。
- 参数错误时不发起 HTTP。

### Day 2：PubMed ESearch / EFetch

目标：

- 实现 PubMed ESearch。
- 实现 PubMed EFetch。
- 实现 timeout、User-Agent、429/5xx retry。

交付：

```text
pubmed_client.py
tests/test_pubmed_client.py
```

完成标准：

- 能用 mock response 返回 PMID。
- 能用 mock response 返回 XML。
- 429/503 重试逻辑测试通过。
- 测试不访问真实网络。

### Day 3：raw 保存和 XML 解析

目标：

- 保存 ESearch 原始 JSON。
- 保存 EFetch 原始 XML。
- 解析 PubMed XML 为论文结构。

交付：

```text
pubmed_storage.py raw 部分
pubmed_parser.py
tests/fixtures/pubmed_esearch_response.json
tests/fixtures/pubmed_efetch_response.xml
tests/test_pubmed_parser.py
tests/test_pubmed_storage.py 初版
```

完成标准：

- 原始响应保存到 `data/raw/pubmed`。
- PMID、DOI、标题、摘要、期刊、日期、作者、机构可解析。
- 多段摘要可合并。

### Day 4：邮箱解析和客户候选线索

目标：

- 从 affiliation 提取邮箱。
- 校验邮箱格式。
- 记录邮箱来源和姓名对应置信度。
- 生成 PI/通讯作者候选线索。

交付：

```text
pubmed_leads.py
tests/test_pubmed_leads.py
```

完成标准：

- 邮箱只来自 affiliation。
- 无邮箱标记 `missing`。
- 无效邮箱不作为 verified email。
- high/medium/low 置信度逻辑可测试。
- 最后一作者可生成 PI 候选并标记推断。

### Day 5：临时评分、导出和任务报告

目标：

- 实现 PubMed 单源临时评分。
- 导出 papers JSON/CSV。
- 导出 leads JSON/CSV。
- 输出 run report。

交付：

```text
pubmed_scoring.py
pubmed_storage.py processed/report 部分
tests/test_pubmed_scoring.py
tests/test_pubmed_storage.py 完整版
```

完成标准：

- 每条 lead 有 score、priority、score_explanation。
- 导出字段齐全。
- CSV Excel 打开不乱码。
- run report 包含输入、统计、文件路径和错误信息。

### Day 6：端到端串联和 README

目标：

- 串联完整 CLI 流程。
- 更新 README。
- 准备演示命令。

交付：

```text
pubmed_main.py 完整版
README.md 更新
tests/test_pubmed_main.py 完整版
```

完成标准：

- mock 端到端测试通过。
- 命令行输出统计和文件路径。
- README 能指导运行 PubMed 第一轮。

### Day 7：自测、修复和演示材料

目标：

- 运行全部测试。
- 修复问题。
- 准备演示材料和验收说明。

交付：

```text
PubMed 第一轮自测结果
PubMed 第一轮演示脚本
已知限制说明
```

完成标准：

- 全部 pytest 通过。
- 测试无真实网络访问。
- 演示流程可重复执行。

## 30. 开发任务清单

| 编号 | 任务 | 文件 | 优先级 | 完成标准 |
| --- | --- | --- | --- | --- |
| P1-01 | PubMed 参数模型 | `pubmed_models.py` | P0 | 参数校验全部通过 |
| P1-02 | PubMed CLI 骨架 | `pubmed_main.py` | P0 | `--help` 正常 |
| P1-03 | ESearch 请求 | `pubmed_client.py` | P0 | mock 返回 PMID |
| P1-04 | EFetch 请求 | `pubmed_client.py` | P0 | mock 返回 XML |
| P1-05 | HTTP 重试 | `pubmed_client.py` | P0 | 429/5xx retry 测试通过 |
| P1-06 | raw 保存 | `pubmed_storage.py` | P0 | ESearch/EFetch 原始数据落盘 |
| P1-07 | XML 解析 | `pubmed_parser.py` | P0 | 核心字段解析通过 |
| P1-08 | DOI 标准化 | `pubmed_parser.py` | P0 | DOI 格式统一 |
| P1-09 | 作者解析 | `pubmed_parser.py` | P0 | 作者顺序、末位作者正确 |
| P1-10 | affiliation 解析 | `pubmed_parser.py` | P0 | 原始机构文本保留 |
| P1-11 | 邮箱提取 | `pubmed_leads.py` | P0 | 只从 affiliation 提取 |
| P1-12 | 邮箱姓名对应 | `pubmed_leads.py` | P0 | 置信度字段正确 |
| P1-13 | Lead 生成 | `pubmed_leads.py` | P0 | 可生成候选客户 |
| P1-14 | Lead 去重 | `pubmed_leads.py` | P1 | 同邮箱去重 |
| P1-15 | 国家识别 | `pubmed_leads.py` | P1 | unknown/置信度可输出 |
| P1-16 | 关键词匹配 | `pubmed_scoring.py` | P0 | matched_keywords 可输出 |
| P1-17 | 临时评分 | `pubmed_scoring.py` | P0 | 分数和优先级正确 |
| P1-18 | papers 导出 | `pubmed_storage.py` | P0 | JSON/CSV 输出 |
| P1-19 | leads 导出 | `pubmed_storage.py` | P0 | JSON/CSV 输出 |
| P1-20 | run report | `pubmed_storage.py` | P0 | 统计和文件路径完整 |
| P1-21 | 端到端测试 | `test_pubmed_main.py` | P0 | mock 全流程通过 |
| P1-22 | README 更新 | `README.md` | P1 | 有运行方法和限制 |

## 31. 每个模块的职责边界

### `pubmed_models.py`

只负责数据结构和参数校验。

不做：

- HTTP 请求。
- XML 解析。
- 文件保存。
- 评分。

### `pubmed_client.py`

只负责 PubMed API 请求。

负责：

- ESearch。
- EFetch。
- 参数构造。
- User-Agent。
- timeout。
- retry。

不做：

- XML 字段解析。
- 客户线索生成。
- 评分。
- 导出。

### `pubmed_parser.py`

只负责把 PubMed XML 解析成结构化论文。

负责：

- PMID。
- DOI。
- 标题。
- 摘要。
- 期刊。
- 日期。
- 作者。
- affiliation。
- MeSH。
- keywords。

不做：

- HTTP 请求。
- Lead 生成。
- 评分。
- 文件导出。

### `pubmed_leads.py`

只负责从论文和作者中生成客户候选线索。

负责：

- 邮箱提取。
- 邮箱格式校验。
- 邮箱来源。
- 邮箱姓名对应置信度。
- PI/通讯作者候选。
- Lead 去重。
- 数据质量标记。

不做：

- HTTP 请求。
- XML 解析。
- 文件保存。

### `pubmed_scoring.py`

只负责 PubMed 单源临时评分。

负责：

- 关键词匹配。
- 研究方向匹配分。
- 发表时效性分。
- 邮箱可联系性分。
- 优先级分层。
- 评分解释。

不做：

- 正式四维评分。
- 基金评分。
- LLM 推荐理由。

### `pubmed_storage.py`

只负责文件保存。

负责：

- raw JSON/XML。
- processed JSON/CSV。
- run report。
- 安全文件名。
- 原子写入。
- Excel 兼容 CSV 编码。

不做：

- HTTP 请求。
- XML 解析。
- 评分。

### `pubmed_main.py`

只负责流程编排。

负责：

- CLI。
- 调用各模块。
- 输出运行摘要。

不做：

- 复杂业务逻辑。
- 字段解析细节。
- 评分细节。

## 32. Definition of Done

PubMed 第一轮完成需要同时满足：

1. CLI 可创建 PubMed 检索任务。
2. ESearch 和 EFetch 均可通过 mock 测试。
3. 原始响应先保存。
4. 解析结果包含论文核心字段。
5. 邮箱只来自 affiliation。
6. 邮箱来源链接完整。
7. 邮箱和姓名对应关系有置信度。
8. 无邮箱有缺失标记。
9. 能生成 PI/通讯作者候选线索。
10. 能输出 PubMed 单源临时评分。
11. 明确标记基金源未接入。
12. 能导出 papers JSON/CSV。
13. 能导出 leads JSON/CSV。
14. 能生成 run report。
15. README 更新。
16. 全部 pytest 通过。
17. 测试不访问真实网络。
18. 文档说明 PubMed 单源不是最终完整交付。

## 33. 甲方需要确认的问题

开发前建议确认：

1. PubMed 第一轮 `max_results` 限制是否接受 100。
2. 第一轮是否接受“PI/通讯作者候选”口径，而不是“已确认 PI”。
3. 无邮箱线索是否保留。
4. 邮箱低置信度记录是否进入人工确认，而不是直接导出为 verified email。
5. PubMed 单源临时评分是否仅用于 Demo，不作为正式四维评分。
6. 第一轮是否只导出 JSON/CSV，不做页面。
7. 第一轮是否不调用 LLM。
8. 第一轮是否不发送真实邮件。
9. 目标服务类型关键词是否由甲方提供。
10. CSV 字段是否采用本文档中的字段列表。

## 34. 第一轮交付物

代码交付：

- PubMed 采集模块。
- PubMed XML 解析模块。
- PubMed lead 生成模块。
- PubMed 临时评分模块。
- PubMed 导出模块。
- PubMed CLI。
- pytest 测试。

数据交付：

- `data/raw/pubmed/*_esearch.json`
- `data/raw/pubmed/*_efetch.xml`
- `data/raw/pubmed/*_request_meta.json`
- `data/processed/pubmed/*_papers.json`
- `data/processed/pubmed/*_papers.csv`
- `data/processed/pubmed/*_leads.json`
- `data/processed/pubmed/*_leads.csv`
- `data/processed/pubmed/*_run_report.json`

文档交付：

- PubMed 第一轮开发方案。
- README 运行说明。
- 自测结果。
- 已知限制说明。

## 35. 后续扩展顺序

PubMed 第一轮完成后，不建议马上做邮件发送。建议顺序：

1. Crossref：补 DOI 和出版元数据。
2. NIH RePORTER 或 NSF：补基金和资金活跃度。
3. ORCID：补作者身份和归并能力。
4. OpenAlex 增强或 bioRxiv/medRxiv：补开放文献和预印本。
5. 正式四维评分。
6. 客户详情和筛选。
7. 个性化英文邮件草稿。
8. 人工审核。
9. 邮件发送和日志。
10. Token 和费用记录。
