# PubMed 第一轮实施方案

版本：v1.0  
日期：2026-08-17  
项目：ScholarLead Agent

## 1. 实施定位

PubMed 第一轮不做完整 AI Agent，也不做完整海外客户开发系统。

本轮目标是先跑通一个稳定的 PubMed 单源主链路 Demo：

```text
关键词输入
→ PubMed 检索
→ 原始数据保存
→ 论文结构化清洗
→ 作者 / 机构 / 邮箱解析
→ PI / 通讯作者候选线索生成
→ PubMed 单源临时评分
→ JSON / CSV 导出
→ 任务报告
```

本轮核心价值是证明项目可以从公开科研数据中生成可检查、可导出、有来源证据的客户候选线索。

## 2. 本轮实现范围

### 2.1 必须实现

- 命令行创建 PubMed 检索任务。
- 支持 `query`、`from_date`、`to_date`、`max_results`。
- 支持可选参数 `country` 和 `service_type`。
- 调用 PubMed 官方 E-utilities。
- 使用 ESearch 获取 PMID 列表。
- 使用 EFetch 获取 PubMed XML。
- 保存 ESearch 原始响应。
- 保存 EFetch 原始 XML。
- 解析论文核心字段。
- 从 affiliation 中提取公开邮箱。
- 记录邮箱来源、来源链接和匹配置信度。
- 无邮箱时标记缺失原因。
- 生成 PI / 通讯作者候选 Lead。
- 生成 PubMed 单源临时评分。
- 输出 papers JSON / CSV。
- 输出 leads JSON / CSV。
- 输出 run report JSON。
- 增加 pytest 测试，测试中必须 mock HTTP。

### 2.2 本轮不实现

- Crossref。
- OpenAlex 增强。
- NIH RePORTER / NSF 基金采集。
- ORCID 作者身份归并。
- bioRxiv / medRxiv。
- Streamlit 或其他网页页面。
- 数据库。
- LLM 调用。
- AI 邮件草稿真实生成。
- 真实邮件发送。
- 批量邮件发送。
- 自动猜测邮箱。
- 复杂客户归并。
- 正式四维评分。

## 3. 输入参数设计

建议命令：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main `
  --query "single cell RNA sequencing cancer" `
  --from-date 2024-01-01 `
  --to-date 2024-12-31 `
  --max-results 100 `
  --country US `
  --service-type scRNA-seq
```

参数说明：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--query` | 是 | 检索关键词或检索短语 |
| `--from-date` | 是 | 开始日期，格式 `YYYY-MM-DD` |
| `--to-date` | 是 | 结束日期，格式 `YYYY-MM-DD` |
| `--max-results` | 是 | 最大结果数，第一轮建议限制为 1 到 100 |
| `--country` | 否 | 目标国家，例如 `US`、`GB`、`JP` |
| `--service-type` | 否 | 目标服务类型，例如 `scRNA-seq`、`RNA-seq` |

校验规则：

- `query` 去除首尾空格后不能为空。
- 日期必须符合 `YYYY-MM-DD`。
- `from_date` 必须早于或等于 `to_date`。
- `max_results` 必须在 1 到 100 之间。
- 参数校验失败时不发起 PubMed 请求。

## 4. 建议新增模块

在 `src/scholarlead_agent/` 下新增以下模块：

| 模块 | 职责 |
| --- | --- |
| `pubmed_models.py` | 定义输入参数、论文、作者、邮箱、Lead、任务报告数据结构 |
| `pubmed_client.py` | 调用 PubMed ESearch / EFetch，处理 timeout、retry、User-Agent |
| `pubmed_parser.py` | 解析 PubMed XML，提取论文、作者、机构、DOI、摘要等字段 |
| `pubmed_leads.py` | 从论文和作者中生成 PI / 通讯作者候选线索 |
| `pubmed_scoring.py` | 计算 PubMed 单源临时评分和优先级 |
| `pubmed_storage.py` | 保存 raw、processed、CSV、JSON、run report |
| `pubmed_main.py` | CLI 主流程编排 |

模块边界：

- `pubmed_client.py` 不做 XML 解析。
- `pubmed_parser.py` 不发 HTTP 请求。
- `pubmed_leads.py` 不做文件保存。
- `pubmed_scoring.py` 不调用 LLM。
- `pubmed_storage.py` 不包含业务评分逻辑。
- `pubmed_main.py` 只负责串联流程，不承载复杂业务细节。

## 5. PubMed 采集方案

使用 NCBI E-utilities，不做网页抓取。

ESearch：

```text
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
```

建议参数：

| 参数 | 值 |
| --- | --- |
| `db` | `pubmed` |
| `term` | query + 日期条件 |
| `retmode` | `json` |
| `retmax` | `max_results` |
| `sort` | `pub date` |
| `tool` | 环境变量 `NCBI_TOOL` |
| `email` | 环境变量 `NCBI_EMAIL` |
| `api_key` | 环境变量 `NCBI_API_KEY`，可选 |

EFetch：

```text
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
```

建议参数：

| 参数 | 值 |
| --- | --- |
| `db` | `pubmed` |
| `id` | PMID 列表，逗号分隔 |
| `retmode` | `xml` |
| `rettype` | `abstract` |
| `tool` | 环境变量 `NCBI_TOOL` |
| `email` | 环境变量 `NCBI_EMAIL` |
| `api_key` | 环境变量 `NCBI_API_KEY`，可选 |

HTTP 要求：

- timeout：30 秒。
- 429 和 5xx 最多重试 3 次。
- 设置清晰 User-Agent。
- 请求失败时记录错误状态和原因。
- ESearch 成功但 EFetch 失败时，保留 ESearch raw 文件。
- EFetch 成功但清洗失败时，保留 EFetch raw XML。

## 6. 原始数据保存

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
  "collected_at": "2026-08-17T10:00:00",
  "status": "success",
  "raw_files": []
}
```

保存原则：

- 先保存 raw，再执行清洗。
- raw 文件不得因后续解析失败而被删除。
- 文件名必须包含 query 和时间戳。
- 后续清洗规则变化时，应能基于 raw 文件重新处理。

## 7. 论文结构化字段

papers 输出字段：

| 字段 | 说明 |
| --- | --- |
| `source` | 固定为 `pubmed` |
| `pmid` | PubMed ID |
| `doi` | 标准化 DOI |
| `title` | 论文标题 |
| `abstract` | 摘要 |
| `journal` | 期刊 |
| `publication_date` | 发表日期 |
| `publication_year` | 发表年份 |
| `article_types` | 文章类型 |
| `mesh_terms` | MeSH 主题词 |
| `keywords` | 关键词 |
| `authors` | 作者列表 |
| `affiliations` | affiliation 文本 |
| `emails` | affiliation 中提取的邮箱 |
| `source_url` | PubMed 页面链接 |
| `raw_record_path` | 原始 XML 文件路径 |

PubMed 链接格式：

```text
https://pubmed.ncbi.nlm.nih.gov/{pmid}/
```

DOI 标准化规则：

- 去除 `https://doi.org/` 前缀。
- 去除 `doi:` 前缀。
- 去除首尾空格。
- 转换为小写。

## 8. 邮箱解析规则

邮箱只允许从 PubMed affiliation 文本中提取，不允许猜测。

必须记录：

- 邮箱。
- 邮箱格式是否有效。
- 邮箱来源类型。
- 邮箱来源链接。
- 邮箱所在 affiliation 文本。
- 匹配作者姓名。
- 姓名和邮箱匹配置信度。

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

匹配规则：

| 场景 | 处理方式 |
| --- | --- |
| 邮箱出现在某作者自己的 affiliation 节点中 | 标记为 high |
| 多个作者共用同一 affiliation 且只有一个邮箱 | 标记为 medium 或需要人工确认 |
| 邮箱无法对应具体作者 | 不绑定具体作者，标记为 needs_review |
| 邮箱格式无效 | 标记为 invalid_format |
| 没有邮箱 | 标记为 missing |

无邮箱时：

```text
email_status = missing
email_reason = source_data_not_provided
queried_sources = PubMed
```

## 9. Lead 生成规则

第一轮不承诺识别“已确认 PI”，只输出：

```text
PI / 通讯作者候选线索
```

生成优先级：

1. 有 high 置信度邮箱的作者。
2. 有 medium 置信度邮箱的作者，但标记需要人工确认。
3. 最后一作者，无邮箱时作为 PI 候选，但标注为推断。
4. 有机构但无邮箱的相关作者。

Lead 字段：

| 字段 | 说明 |
| --- | --- |
| `lead_id` | 本地生成 ID |
| `pi_full_name` | PI / 通讯作者候选姓名 |
| `verified_email` | 已验证邮箱，如有 |
| `email_status` | 邮箱状态 |
| `email_source_url` | 邮箱来源链接 |
| `email_source_type` | 邮箱来源类型 |
| `institution` | 机构 |
| `country` | 国家 |
| `country_confidence` | 国家识别置信度 |
| `recent_publication_title` | 近期论文标题 |
| `abstract` | 摘要 |
| `journal` | 期刊 |
| `publication_year` | 发表年份 |
| `pmid` | PMID |
| `doi` | DOI |
| `author_role` | 作者角色 |
| `matched_keywords` | 命中关键词 |
| `target_service_type` | 目标服务类型 |
| `lead_score` | PubMed 单源临时评分 |
| `priority` | 高 / 中 / 低 |
| `score_explanation` | 评分依据 |
| `data_quality` | 数据质量状态 |
| `source_links` | 来源链接 |

## 10. 去重规则

论文去重：

```text
优先 DOI
没有 DOI 时使用 PMID
```

Lead 去重：

```text
verified_email 相同 → 合并
同一 PMID + 同一作者名 → 合并
姓名相同 + 机构相同 → 标记 candidate，不强制合并
只有姓名相同 → 不合并
```

建议字段：

```text
merge_status = confirmed / candidate / needs_review / not_merged
merge_reason = email_match / same_pmid_author / same_name_institution
```

## 11. PubMed 单源临时评分

正式四维评分需要基金、外包倾向等多数据源支持。PubMed 第一轮只做临时评分，并在导出中明确标记。

临时评分：

| 维度 | 权重 | 依据 |
| --- | ---: | --- |
| 研究方向匹配度 | 50% | title、abstract、MeSH、keywords、query 命中 |
| 发表时效性 | 30% | publication_date 距当前时间 |
| 邮箱可联系性 | 20% | 是否有公开邮箱和来源 |

优先级：

| 分数 | 优先级 |
| --- | --- |
| `>= 80` | 高 |
| `50-79` | 中 |
| `< 50` | 低 |

正式评分占位字段：

```text
funding_activity_score = null
funding_activity_reason = Funding source not connected in PubMed-only first round
outsourcing_tendency_score = null
official_scoring_status = pending_multi_source_data
```

## 12. 输出文件

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

CSV 要求：

- 字段名清晰。
- 日期格式统一。
- 分数为数字。
- 缺失字段有状态说明。
- 使用 Excel 友好的 UTF-8 BOM，避免中文乱码。

## 13. Run Report

每次运行必须生成任务报告。

建议字段：

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

报告用途：

- 方便验收。
- 方便排错。
- 证明 raw 和 processed 文件之间的关系。
- 记录失败原因，避免错误被静默吞掉。

## 14. 开发排期

### Day 1：参数、模型、CLI 骨架

交付：

```text
pubmed_models.py
pubmed_main.py 初版
tests/test_pubmed_models.py
tests/test_pubmed_main.py 初版
```

验收：

- `--help` 可运行。
- 参数校验测试通过。
- 参数错误时不发起 HTTP。

### Day 2：PubMed Client

交付：

```text
pubmed_client.py
tests/test_pubmed_client.py
```

验收：

- mock ESearch 返回 PMID。
- mock EFetch 返回 XML。
- 429 / 5xx retry 测试通过。
- timeout 测试通过。
- 测试不访问真实网络。

### Day 3：Raw 保存和 XML 解析

交付：

```text
pubmed_storage.py raw 部分
pubmed_parser.py
tests/fixtures/pubmed_esearch_response.json
tests/fixtures/pubmed_efetch_response.xml
tests/test_pubmed_parser.py
tests/test_pubmed_storage.py 初版
```

验收：

- 原始响应保存到 `data/raw/pubmed`。
- PMID、DOI、标题、摘要、期刊、日期、作者、机构可解析。
- 多段摘要可合并。

### Day 4：邮箱解析和 Lead 生成

交付：

```text
pubmed_leads.py
tests/test_pubmed_leads.py
```

验收：

- 邮箱只来自 affiliation。
- 无邮箱标记 `missing`。
- 无效邮箱不作为 verified email。
- high / medium / needs_review 置信度逻辑可测试。
- 最后一作者可生成 PI 候选，并标注为推断。

### Day 5：评分、导出和任务报告

交付：

```text
pubmed_scoring.py
pubmed_storage.py processed/report 部分
tests/test_pubmed_scoring.py
tests/test_pubmed_storage.py 完整版
```

验收：

- 每条 lead 有 `lead_score`、`priority`、`score_explanation`。
- papers JSON / CSV 可导出。
- leads JSON / CSV 可导出。
- run report 包含输入、统计、文件路径和错误。

### Day 6：端到端串联和 README 更新

交付：

```text
pubmed_main.py 完整版
README.md 更新
README_cn.md 更新
tests/test_pubmed_main.py 完整版
```

验收：

- mock 端到端流程通过。
- 命令行输出统计和文件路径。
- README 能指导运行 PubMed 第一轮。

### Day 7：自测、修复和演示材料

交付：

```text
完整 pytest 结果
PubMed 第一轮演示命令
已知限制说明
```

验收：

- 全部 pytest 通过。
- 测试无真实网络访问。
- 演示流程可重复执行。

## 15. 测试策略

新增测试文件：

| 测试文件 | 测试内容 |
| --- | --- |
| `test_pubmed_models.py` | 参数校验、模型转换 |
| `test_pubmed_client.py` | ESearch / EFetch、参数、重试、timeout |
| `test_pubmed_parser.py` | XML 解析、摘要、作者、DOI、邮箱文本 |
| `test_pubmed_leads.py` | Lead 生成、邮箱状态、去重 |
| `test_pubmed_scoring.py` | 临时评分和优先级 |
| `test_pubmed_storage.py` | raw / processed / report 保存 |
| `test_pubmed_main.py` | CLI 端到端 mock 流程 |

运行测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

测试原则：

- 不访问真实 PubMed。
- 不访问任何真实网络。
- HTTP 响应必须 mock。
- 不引入 LLM。
- 不发送邮件。
- 不影响已有 OpenAlex 测试。

## 16. 第一轮验收标准

第一轮完成后应能证明：

```text
用户输入关键词和日期
→ 系统从 PubMed 获取论文
→ 保存原始数据
→ 清洗成结构化论文
→ 生成客户候选线索
→ 标记邮箱来源和置信度
→ 给出 PubMed 单源临时评分
→ 导出 JSON / CSV
→ 生成任务报告
```

具体验收点：

- CLI 可运行。
- 参数校验正确。
- ESearch / EFetch 通过 mock 测试。
- 原始数据完整保存。
- 解析结果包含核心论文字段。
- 邮箱只来自 affiliation。
- 无邮箱有明确状态。
- 可生成 PI / 通讯作者候选 Lead。
- Lead 有 PubMed 来源链接。
- 有临时评分和优先级。
- 明确标记基金源未接入。
- papers JSON / CSV 可导出。
- leads JSON / CSV 可导出。
- run report 可生成。
- README 已更新。
- 全部 pytest 通过。
- 测试中不访问真实网络。

## 17. 第一轮交付物

代码交付：

- PubMed 采集模块。
- PubMed XML 解析模块。
- PubMed Lead 生成模块。
- PubMed 临时评分模块。
- PubMed 导出模块。
- PubMed CLI。
- pytest 测试。

数据交付：

```text
data/raw/pubmed/*_esearch.json
data/raw/pubmed/*_efetch.xml
data/raw/pubmed/*_request_meta.json
data/processed/pubmed/*_papers.json
data/processed/pubmed/*_papers.csv
data/processed/pubmed/*_leads.json
data/processed/pubmed/*_leads.csv
data/processed/pubmed/*_run_report.json
```

文档交付：

- README PubMed 运行说明。
- README_cn PubMed 运行说明。
- 第一轮实施方案。
- 已知限制说明。

## 18. 已知限制

- PubMed 单源不能完整判断基金活跃度。
- PubMed 单源不能完整判断外包倾向。
- affiliation 中的机构和国家是自由文本，第一轮只能做基础识别。
- 有邮箱不等于已经完全确认客户身份。
- 最后一作者只能作为 PI 候选，不能直接视为已确认 PI。
- 临时评分只用于 Demo，不等同于正式四维评分。
- 第一轮不生成真实邮件。
- 第一轮不发送邮件。
- 第一轮不调用 LLM。
- 第一轮不接入数据库。

## 19. 后续扩展顺序

PubMed 第一轮完成后，建议按以下顺序扩展：

1. Crossref：补 DOI 和出版元数据。
2. NIH RePORTER / NSF：补基金和资金活跃度。
3. ORCID：补作者身份和归并能力。
4. OpenAlex 增强或 bioRxiv / medRxiv：补开放文献和预印本。
5. 正式四维评分。
6. 客户详情和筛选。
7. 个性化英文邮件草稿。
8. 人工审核流程。
9. 邮件发送和日志。
10. Token 和费用记录。

## 20. 一句话总结

PubMed 第一轮的目标是：先把 PubMed 从“论文检索”跑成“可导出的客户候选线索”，但不碰 LLM、不碰邮件发送、不碰数据库，先把数据链路做稳。

## 21. 第一轮分阶段开发细化

本节用于把第一轮实施拆成可执行的开发阶段。每个阶段都必须明确“要做什么”和“做完后应该得到什么结果”。如果某一阶段没有通过验收，不建议继续叠加后续复杂功能。

### 阶段 1：项目准备与边界确认

目标：确认 PubMed 第一轮只做单源主链路，不扩展到 LLM、邮件、数据库或多数据源。

需要做：

- 确认当前包名为 `scholarlead_agent`。
- 确认继续使用 `src` 项目结构。
- 确认 Python 支持版本为 3.11 及以上。
- 确认本轮只新增 PubMed 相关模块。
- 确认不修改 OpenAlex 已有可用功能。
- 确认本轮测试不访问真实网络。
- 确认输出目录：
  - `data/raw/pubmed`
  - `data/processed/pubmed`

需要得到的结果：

- 开发边界明确。
- PubMed 第一轮不会误加入 Crossref、LLM、Streamlit、数据库或邮件发送。
- 后续每个模块的职责清楚。
- 项目仍能通过已有 OpenAlex 测试。

阶段验收：

- 可以说清楚本轮“做什么”和“不做什么”。
- `README.md`、`README_cn.md` 或实施文档中明确写出第一轮限制。

### 阶段 2：参数模型与命令行骨架

目标：先让 PubMed 命令行入口成立，但暂不访问 PubMed。

需要做：

- 新增 `src/scholarlead_agent/pubmed_models.py`。
- 新增 `src/scholarlead_agent/pubmed_main.py`。
- 定义 PubMed 检索参数模型：
  - `query`
  - `from_date`
  - `to_date`
  - `max_results`
  - `country`
  - `service_type`
  - `raw_dir`
  - `processed_dir`
- 实现参数校验：
  - `query` 不能为空。
  - 日期格式必须是 `YYYY-MM-DD`。
  - `from_date <= to_date`。
  - `max_results` 第一轮限制为 1 到 100。
- 实现 CLI `--help`。
- 参数错误时直接退出，不发起 HTTP 请求。

需要得到的结果：

- 可以运行：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main --help
```

- 参数错误时能看到清晰错误信息。
- 参数正确时能生成内部 `SearchParams` 或类似结构。

建议测试：

- `tests/test_pubmed_models.py`
- `tests/test_pubmed_main.py`

阶段验收：

- `--help` 正常显示。
- 日期错误会失败。
- `max_results=0` 会失败。
- `max_results=101` 会失败。
- 空 query 会失败。
- 参数校验失败时不会调用任何 HTTP client。

### 阶段 3：PubMed API Client

目标：实现 PubMed 官方 API 调用能力，但测试中全部 mock。

需要做：

- 新增 `src/scholarlead_agent/pubmed_client.py`。
- 实现 ESearch 请求构造。
- 实现 EFetch 请求构造。
- 使用 NCBI E-utilities：
  - `esearch.fcgi`
  - `efetch.fcgi`
- 设置请求 timeout 为 30 秒。
- 设置清晰 User-Agent，例如 `ScholarLeadAgent/0.1`。
- 对 429 和 5xx 最多重试 3 次。
- 从环境变量读取：
  - `NCBI_TOOL`
  - `NCBI_EMAIL`
  - `NCBI_API_KEY`
- 不在代码中写真实邮箱、密码或 API Key。
- 请求失败时抛出清晰异常或返回可记录的错误状态。

需要得到的结果：

- ESearch 可以返回 PMID 列表。
- EFetch 可以返回 XML 文本。
- retry、timeout 和 HTTP 错误行为可测试。
- Client 层只负责请求，不解析 XML，不生成 Lead。

建议测试：

- `tests/test_pubmed_client.py`

阶段验收：

- mock ESearch 成功响应可解析出 PMID。
- mock EFetch 成功响应可拿到 XML。
- 429 会触发重试。
- 503 会触发重试。
- 400 不应盲目重试。
- timeout 有清晰错误。
- 测试不访问真实 PubMed。

### 阶段 4：原始数据保存

目标：确保 API 返回的数据先落盘，再进入清洗解析。

需要做：

- 新增或扩展 `src/scholarlead_agent/pubmed_storage.py`。
- 创建目录：
  - `data/raw/pubmed`
  - `data/processed/pubmed`
- 实现安全文件名生成：
  - 包含 query。
  - 包含时间戳。
  - 去除不适合文件名的字符。
- 保存 ESearch 原始 JSON。
- 保存 EFetch 原始 XML。
- 保存 request meta。
- 保存失败状态和错误原因。
- 保证后续解析失败不会删除 raw 文件。

需要得到的结果：

```text
data/raw/pubmed/{safe_query}_{timestamp}_esearch.json
data/raw/pubmed/{safe_query}_{timestamp}_efetch.xml
data/raw/pubmed/{safe_query}_{timestamp}_request_meta.json
```

建议测试：

- `tests/test_pubmed_storage.py`

阶段验收：

- raw 文件可以正常写入。
- 文件名包含 query 和 timestamp。
- JSON 可重新读取。
- XML 内容保持原样。
- 保存函数不依赖网络。
- 解析失败时 raw 文件仍存在。

### 阶段 5：PubMed XML 解析

目标：把 PubMed XML 转为结构化论文数据。

需要做：

- 新增 `src/scholarlead_agent/pubmed_parser.py`。
- 使用 XML 解析器解析 PubMed XML。
- 提取论文核心字段：
  - `pmid`
  - `doi`
  - `title`
  - `abstract`
  - `journal`
  - `publication_date`
  - `publication_year`
  - `article_types`
  - `mesh_terms`
  - `keywords`
  - `authors`
  - `affiliations`
  - `source_url`
  - `raw_record_path`
- 处理多段摘要。
- 处理缺失摘要。
- 处理缺失 DOI。
- 标准化 DOI：
  - 去除 `https://doi.org/`
  - 去除 `doi:`
  - 去除首尾空格
  - 转小写
- 保留原始 affiliation 文本。

需要得到的结果：

- 一组结构化 paper 对象。
- 每篇 paper 都有 PubMed 来源链接。
- 缺失字段不会导致整个解析崩溃。

建议测试：

- `tests/fixtures/pubmed_efetch_response.xml`
- `tests/test_pubmed_parser.py`

阶段验收：

- 能解析 PMID。
- 能解析标题。
- 能解析摘要。
- 能解析 DOI 并标准化。
- 能解析作者顺序。
- 能识别最后一作者。
- 能保留 affiliation。
- XML 缺少某字段时程序不崩溃。

### 阶段 6：邮箱提取与邮箱证据

目标：只从 PubMed affiliation 中提取邮箱，并保留证据链。

需要做：

- 在 `pubmed_leads.py` 或单独 helper 中实现邮箱提取。
- 使用保守邮箱正则。
- 从 affiliation 文本中提取邮箱。
- 校验邮箱格式。
- 记录邮箱来源：
  - `email_source_type = pubmed_affiliation`
  - `email_source_url`
  - `matched_affiliation`
- 判断邮箱和作者关系置信度：
  - `high`
  - `medium`
  - `needs_review`
  - `missing`
  - `invalid_format`
- 不根据姓名拼接邮箱。
- 不根据机构域名猜邮箱。
- 不访问外部网页补邮箱。

需要得到的结果：

- 每个邮箱都有来源。
- 每个邮箱都有状态。
- 无邮箱时有缺失原因。
- 不会出现猜测邮箱。

建议测试：

- `tests/test_pubmed_leads.py`

阶段验收：

- affiliation 中有邮箱时能提取。
- affiliation 中无邮箱时标记 missing。
- 无效邮箱不进入 verified email。
- 多作者共用 affiliation 时不强行高置信绑定。
- 邮箱来源链接为 PubMed 页面链接。

### 阶段 7：论文去重

目标：避免同一论文重复进入后续 Lead 生成。

需要做：

- 在解析后或 storage 前实现论文去重。
- 优先按 DOI 去重。
- 没有 DOI 时按 PMID 去重。
- 保留去重依据。
- 不删除 raw 文件。

需要得到的结果：

- processed papers 中无重复 DOI。
- 无 DOI 的记录按 PMID 去重。
- 去重逻辑可测试。

建议测试：

- `tests/test_pubmed_parser.py` 或 `tests/test_pubmed_storage.py`

阶段验收：

- 两条相同 DOI 的记录只保留一条。
- 两条相同 PMID 的无 DOI 记录只保留一条。
- DOI 不同但标题相似时不强行合并。

### 阶段 8：Lead 生成

目标：从论文和作者信息生成 PI / 通讯作者候选线索。

需要做：

- 新增 `src/scholarlead_agent/pubmed_leads.py`。
- 根据 paper 和 author 生成 lead。
- 优先生成有 high 置信邮箱的作者 lead。
- medium 置信邮箱生成 lead，但标记需要人工确认。
- 无邮箱时，最后一作者可作为 PI 候选。
- 有机构但无邮箱的作者可保留为无邮箱候选。
- 每条 lead 保留：
  - 姓名
  - 邮箱状态
  - 机构
  - 国家
  - 论文标题
  - PMID
  - DOI
  - PubMed 来源链接
  - 作者角色
  - 数据质量状态

需要得到的结果：

- 可导出的候选客户列表。
- 有邮箱 lead 和无邮箱 lead 都有明确状态。
- 最后一作者不会被写成“已确认 PI”，只写成候选。

建议测试：

- `tests/test_pubmed_leads.py`

阶段验收：

- 有邮箱作者生成可联系 lead。
- 无邮箱最后一作者生成候选 lead。
- Lead 中包含 PubMed source_url。
- Lead 中包含 email_status。
- Lead 中包含 data_quality。

### 阶段 9：Lead 去重与人工审核标记

目标：减少明显重复 Lead，同时避免错误合并科研人员。

需要做：

- 在 `pubmed_leads.py` 中实现基础 Lead 去重。
- 规则：
  - verified_email 相同可以合并。
  - 同一 PMID + 同一作者名可以合并。
  - 姓名相同 + 机构相同标记 candidate，不强制合并。
  - 只有姓名相同不合并。
- 增加字段：
  - `merge_status`
  - `merge_reason`
  - `manual_review_required`

需要得到的结果：

- 明显重复邮箱不会重复出现。
- 弱匹配不会被错误合并。
- 需要人工确认的记录有标记。

建议测试：

- `tests/test_pubmed_leads.py`

阶段验收：

- 同邮箱 lead 合并。
- 同 PMID 同作者 lead 合并。
- 仅姓名相同不合并。
- 弱匹配记录进入人工审核状态。

### 阶段 10：国家与机构基础识别

目标：从 affiliation 中做基础国家和机构识别，但不把推断当成事实。

需要做：

- 保留 `raw_affiliation`。
- 尝试从 affiliation 中识别常见国家：
  - United States / USA / US
  - United Kingdom / UK
  - China
  - Japan
  - Germany
  - France
  - Canada
  - Australia
- 可用邮箱域名作辅助，但不能作为唯一强证据。
- 无法识别时标记 `unknown`。
- 记录：
  - `country`
  - `country_confidence`
  - `country_source`

需要得到的结果：

- Lead 中有基础国家字段。
- 无法确认时不会乱猜。
- affiliation 原文保留。

建议测试：

- `tests/test_pubmed_leads.py`

阶段验收：

- 常见国家可识别。
- 无法识别时输出 `unknown`。
- 有 country_confidence。
- 有 country_source。

### 阶段 11：关键词匹配与服务类型标记

目标：根据 query、论文标题、摘要、MeSH 和关键词判断研究方向匹配情况。

需要做：

- 新增 `src/scholarlead_agent/pubmed_scoring.py`。
- 实现关键词分词或简单标准化。
- 在以下字段中匹配：
  - query
  - title
  - abstract
  - mesh_terms
  - keywords
- 保存：
  - `matched_keywords`
  - `target_service_type`
  - `topic_match_reason`
- 如果用户提供 `service_type`，写入 Lead。
- 不使用 LLM 判断研究方向。

需要得到的结果：

- 每条 lead 有关键词命中信息。
- 后续评分可以使用匹配结果。

建议测试：

- `tests/test_pubmed_scoring.py`

阶段验收：

- title 命中关键词可识别。
- abstract 命中关键词可识别。
- MeSH 命中关键词可识别。
- service_type 能进入导出字段。

### 阶段 12：PubMed 单源临时评分

目标：给候选 Lead 一个 Demo 用临时优先级，不冒充正式四维评分。

需要做：

- 在 `pubmed_scoring.py` 中实现评分。
- 临时评分维度：
  - 研究方向匹配度 50%。
  - 发表时效性 30%。
  - 邮箱可联系性 20%。
- 实现优先级：
  - `>= 80`：高。
  - `50-79`：中。
  - `< 50`：低。
- 输出评分解释。
- 明确写入：
  - `funding_activity_score = null`
  - `funding_activity_reason = Funding source not connected in PubMed-only first round`
  - `outsourcing_tendency_score = null`
  - `official_scoring_status = pending_multi_source_data`

需要得到的结果：

- 每条 lead 有分数。
- 每条 lead 有优先级。
- 每条 lead 有评分解释。
- 清楚标记这不是正式评分。

建议测试：

- `tests/test_pubmed_scoring.py`

阶段验收：

- 有邮箱、近期发表、关键词匹配的 lead 分数较高。
- 无邮箱、较旧发表、弱匹配的 lead 分数较低。
- priority 分层正确。
- funding 未接入说明存在。

### 阶段 13：Processed 数据导出

目标：把 papers 和 leads 同时导出为 JSON 和 CSV。

需要做：

- 在 `pubmed_storage.py` 中实现：
  - `save_pubmed_papers_json`
  - `save_pubmed_papers_csv`
  - `save_pubmed_leads_json`
  - `save_pubmed_leads_csv`
- CSV 使用 Excel 友好的 UTF-8 BOM。
- 列名清楚。
- 缺失值保留状态说明，不要空白混淆。
- 文件名包含 query 和 timestamp。

需要得到的结果：

```text
data/processed/pubmed/pubmed_papers_{safe_query}_{timestamp}.json
data/processed/pubmed/pubmed_papers_{safe_query}_{timestamp}.csv
data/processed/pubmed/pubmed_leads_{safe_query}_{timestamp}.json
data/processed/pubmed/pubmed_leads_{safe_query}_{timestamp}.csv
```

建议测试：

- `tests/test_pubmed_storage.py`

阶段验收：

- papers JSON 可读。
- papers CSV 可读。
- leads JSON 可读。
- leads CSV 可读。
- CSV 中文不乱码。
- 导出字段和文档一致。

### 阶段 14：Run Report 生成

目标：每次运行都有可追踪报告，便于验收和排错。

需要做：

- 在 `pubmed_storage.py` 中实现 run report。
- 记录：
  - task_id
  - source
  - query
  - from_date
  - to_date
  - max_results
  - pmid_count
  - paper_count
  - lead_count
  - leads_with_email_count
  - missing_email_count
  - raw_files
  - processed_files
  - errors
  - started_at
  - finished_at
  - status
- 成功和失败都生成报告，或至少在失败后尽量生成报告。

需要得到的结果：

```text
data/processed/pubmed/pubmed_run_report_{safe_query}_{timestamp}.json
```

建议测试：

- `tests/test_pubmed_storage.py`
- `tests/test_pubmed_main.py`

阶段验收：

- 报告能定位 raw 文件。
- 报告能定位 processed 文件。
- 报告包含统计数字。
- 失败时有错误信息。

### 阶段 15：端到端 CLI 串联

目标：把前面所有模块串成一个完整可运行流程。

需要做：

- 完善 `pubmed_main.py`。
- 串联流程：

```text
parse args
→ validate inputs
→ fetch PMIDs
→ save ESearch raw
→ fetch XML
→ save EFetch raw
→ parse papers
→ deduplicate papers
→ save paper outputs
→ build leads
→ deduplicate leads
→ score leads
→ save lead outputs
→ save run report
→ print summary
```

- 终端输出关键信息：
  - PMIDs collected
  - Papers parsed
  - Leads generated
  - Leads with verified email
  - Raw file paths
  - Processed file paths
  - Run report path

需要得到的结果：

- 一条命令可以跑完整流程。
- 成功后能看到统计摘要。
- 失败时能看到清晰错误。
- 已保存文件不会被后续失败删除。

建议测试：

- `tests/test_pubmed_main.py`

阶段验收：

- mock 端到端测试通过。
- CLI 输出包含统计。
- CLI 输出包含文件路径。
- 不访问真实网络。

### 阶段 16：README 与中文文档更新

目标：让新同事按文档即可运行 PubMed 第一轮。

需要做：

- 更新 `README.md`。
- 更新 `README_cn.md`。
- 保留第一轮限制说明。
- 增加 PubMed 运行命令。
- 增加输出文件说明。
- 增加测试命令。
- 增加环境变量说明：
  - `NCBI_TOOL`
  - `NCBI_EMAIL`
  - `NCBI_API_KEY`
- 更新 `.env.example`，只写占位值。

需要得到的结果：

- README 中有 PubMed 第一轮运行方法。
- README 中明确不调用 LLM、不发送邮件、不接数据库。
- `.env.example` 无真实密钥。

阶段验收：

- 按 README 可以安装、运行、测试。
- 文档不会让人误以为第一轮已经完成完整 Agent。

### 阶段 17：完整测试与回归

目标：确认 PubMed 新功能不破坏已有 OpenAlex 功能。

需要做：

- 运行全部测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

- 确认 OpenAlex 测试仍通过。
- 确认 PubMed 测试通过。
- 确认测试中无真实网络访问。
- 检查生成文件是否进入 `.gitignore` 应忽略范围。
- 检查没有提交 `.env`、API Key、密码。

需要得到的结果：

- 全部 pytest 通过。
- 无真实网络测试。
- 无密钥泄露。
- 文档和代码一致。

阶段验收：

- 测试结果为 passed。
- 失败测试必须修复后再交付。
- 如果只做 mock 测试，交付说明中必须明确。

### 阶段 18：演示与验收材料

目标：准备给师姐或甲方看的第一轮演示材料。

需要做：

- 准备一条演示命令。
- 展示 raw 文件。
- 展示 papers CSV。
- 展示 leads CSV。
- 展示 run report。
- 说明邮箱来源和置信度。
- 说明 PubMed 单源临时评分。
- 说明本轮限制。

需要得到的结果：

- 可以清楚演示：

```text
用户输入关键词
→ PubMed 返回论文
→ 系统保存 raw
→ 系统生成结构化论文
→ 系统生成客户候选线索
→ 系统导出结果
```

演示话术：

```text
本轮只验证 PubMed 单源主链路，已完成关键词检索、数据采集、原始数据保存、结构化清洗、邮箱证据、客户候选线索、临时评分和导出。
正式四维评分、基金信息、客户归并、LLM 邮件草稿和真实邮件发送，将在后续多源阶段完成。
```

阶段验收：

- 演示流程可重复。
- 输出文件可打开。
- 限制说明清楚。
- 不夸大第一轮能力。

## 22. 第一轮阶段交付总表

| 阶段 | 主要任务 | 需要得到的结果 | 关键验收 |
| --- | --- | --- | --- |
| 阶段 1 | 项目准备与边界确认 | 明确只做 PubMed 单源主链路 | 不引入 LLM、数据库、邮件发送 |
| 阶段 2 | 参数模型与 CLI 骨架 | `--help` 可运行，参数可校验 | 参数错误不发 HTTP |
| 阶段 3 | PubMed API Client | mock ESearch / EFetch 可用 | timeout、retry、错误处理通过测试 |
| 阶段 4 | 原始数据保存 | raw JSON / XML / meta 落盘 | raw 先保存，失败不删除 |
| 阶段 5 | XML 解析 | 结构化 paper 数据 | PMID、DOI、标题、摘要、作者可解析 |
| 阶段 6 | 邮箱提取 | 邮箱和证据链 | 只从 affiliation 提取，不猜测 |
| 阶段 7 | 论文去重 | 去重后的 papers | DOI 优先，无 DOI 用 PMID |
| 阶段 8 | Lead 生成 | PI / 通讯作者候选线索 | 有邮箱和无邮箱状态清楚 |
| 阶段 9 | Lead 去重 | 去重和人工审核标记 | 弱匹配不强制合并 |
| 阶段 10 | 国家与机构基础识别 | country、institution、confidence | 不确定时标记 unknown |
| 阶段 11 | 关键词匹配 | matched_keywords、topic_match_reason | 不使用 LLM |
| 阶段 12 | 临时评分 | lead_score、priority、explanation | 明确不是正式四维评分 |
| 阶段 13 | processed 导出 | papers/leads JSON 和 CSV | CSV 可读，字段完整 |
| 阶段 14 | run report | 任务报告 JSON | 包含统计、路径和错误 |
| 阶段 15 | CLI 串联 | 一条命令跑完整流程 | mock 端到端通过 |
| 阶段 16 | 文档更新 | README 和 README_cn 可指导运行 | 边界和命令清楚 |
| 阶段 17 | 完整测试 | 全部 pytest 通过 | 不访问真实网络 |
| 阶段 18 | 演示材料 | 可复现演示流程 | 不夸大第一轮能力 |
