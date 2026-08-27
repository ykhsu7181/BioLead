# ScholarLead Agent 当前系统字段说明

版本：v0.1  
日期：2026-08-24  
范围：当前已实现的 PubMed、Crossref、OpenAlex、统一模型、Agent Tool、邮件草稿、AI 使用记录和配置字段。

## 1. 总体说明

当前系统还不是最终生产版，字段会随着 NIH RePORTER、ORCID、数据库、正式评分和邮件审核发送继续扩展。

当前字段主要来自：

- PubMed 主链路；
- Crossref 元数据补充；
- OpenAlex 元数据补充；
- 多源统一模型；
- Agent Tool；
- 英文邮件草稿；
- AI usage / Token 记录；
- Streamlit 展示和导出文件。

字段原则：

- raw 原始数据先保存；
- processed 字段必须可追溯；
- 邮箱不猜测；
- 基金不猜测；
- 候选 PI 不等于已确认通讯作者；
- PubMed 临时评分不等于正式四维评分；
- 邮件草稿不等于真实发送。

---

# 2. PubMed 字段

## 2.1 PubMedSearchParams

用途：PubMed 检索输入参数。

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `query` | str | 检索关键词 | 必填，不能为空 |
| `from_date` | str | 开始日期 | `YYYY-MM-DD` |
| `to_date` | str | 结束日期 | `YYYY-MM-DD` |
| `max_results` | int | 最大结果数 | 当前上限 100 |
| `country` | str/null | 目标国家标签 | 可选，用于任务上下文 |
| `service_type` | str/null | 目标服务类型 | 可选，如 `scRNA-seq` |
| `raw_dir` | Path | raw 输出目录 | 默认 `data/raw/pubmed` |
| `processed_dir` | Path | processed 输出目录 | 默认 `data/processed/pubmed` |

## 2.2 PubMedAuthor

用途：PubMed XML 中解析出的作者信息。

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `full_name` | str | 作者全名 | 由 fore name / last name 组合 |
| `last_name` | str | 姓 | PubMed 原始字段 |
| `fore_name` | str | 名 | PubMed 原始字段 |
| `initials` | str | 缩写 | PubMed 原始字段 |
| `author_position` | int | 作者顺序 | 从 1 开始 |
| `is_last_author` | bool | 是否末位作者 | 用于候选 PI 判断 |
| `affiliations` | list[str] | 作者机构文本 | 邮箱也可能出现在这里 |

## 2.3 PubMedPaper

用途：清洗后的 PubMed 论文记录。

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `source` | str | 数据源 | 固定为 `pubmed` |
| `pmid` | str | PubMed ID | 论文唯一标识之一 |
| `doi` | str/null | DOI | 可能为空 |
| `title` | str | 论文标题 | 来自 PubMed |
| `abstract` | str | 摘要 | 可能为空 |
| `journal` | str | 期刊名称 | 来自 PubMed |
| `publication_date` | str | 发表日期 | 可能只有年月或年份 |
| `publication_year` | int/null | 发表年份 | 解析失败为空 |
| `article_types` | list[str] | 文章类型 | 如 Journal Article |
| `mesh_terms` | list[str] | MeSH 词 | PubMed 主题词 |
| `keywords` | list[str] | 关键词 | 作者关键词或 XML 中关键词 |
| `authors` | list[PubMedAuthor] | 作者列表 | 包含机构文本 |
| `affiliations` | list[str] | 全文机构文本集合 | 用于邮箱、机构、国家识别 |
| `source_url` | str | PubMed 链接 | 如 `https://pubmed.ncbi.nlm.nih.gov/{pmid}/` |
| `raw_record_path` | str/null | raw XML 文件路径 | 用于追溯 |

## 2.4 PubMedEmailEvidence

用途：从 PubMed affiliation 中提取到的邮箱证据。

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `email` | str/null | 邮箱地址 | 只来自公开 affiliation 文本 |
| `email_status` | str | 邮箱状态 | 如 `verified_from_pubmed_affiliation` / `missing` |
| `email_source_type` | str | 邮箱来源类型 | 当前主要是 `pubmed_affiliation` |
| `email_source_url` | str | 邮箱来源链接 | PubMed 页面链接 |
| `matched_author_name` | str/null | 匹配到的作者名 | 可能为空 |
| `matched_affiliation` | str/null | 匹配邮箱的机构文本 | 原始 affiliation 片段 |
| `name_email_match_confidence` | str | 姓名邮箱匹配置信度 | 如 high / medium / missing |
| `email_reason` | str/null | 邮箱判断说明 | 可为空 |

## 2.5 PubMedLead

用途：PubMed 单源生成的候选客户 / 候选 PI 线索。

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `lead_id` | str | Lead ID | 系统生成 |
| `pi_full_name` | str | 候选 PI / 候选联系人姓名 | 不是绝对确认通讯作者 |
| `verified_email` | str/null | 已验证公开邮箱 | 无邮箱时为空 |
| `email_status` | str | 邮箱状态 | verified / missing 等 |
| `email_source_url` | str | 邮箱来源链接 | PubMed 链接 |
| `email_source_type` | str | 邮箱来源类型 | PubMed affiliation |
| `name_email_match_confidence` | str | 姓名邮箱匹配置信度 | high / medium / missing |
| `institution` | str/null | 机构名称 | 基础规则识别 |
| `country` | str | 国家 | 无法判断为 `unknown` |
| `country_confidence` | str | 国家置信度 | high / medium / unknown |
| `country_source` | str | 国家判断来源 | 如 `affiliation_text` |
| `raw_affiliation` | str/null | 原始机构文本 | 必须保留 |
| `recent_publication_title` | str | 近期论文标题 | 来自 PubMedPaper |
| `abstract` | str | 摘要 | 用于邮件草稿和分析 |
| `journal` | str | 期刊 | 来自 PubMed |
| `publication_year` | int/null | 发表年份 | 可能为空 |
| `pmid` | str | PMID | 来源论文 |
| `doi` | str/null | DOI | 可能为空 |
| `author_role` | str | 作者角色 | 如 email_author / candidate_pi_last_author |
| `source_links` | list[str] | 来源链接 | 至少包含 PubMed 链接 |
| `data_quality` | str | 数据质量标签 | 如 email_evidence_available / missing_email_candidate |
| `manual_review_required` | bool | 是否需要人工审核 | 邮箱缺失或证据弱时为 true |
| `notes` | str | 备注 | 规则说明 |
| `merge_status` | str | 合并状态 | 当前默认 `not_merged` |
| `merge_reason` | str/null | 合并原因 | 当前多为空 |
| `matched_keywords` | list[str] | 匹配关键词 | 来自 query / service type 匹配 |
| `target_service_type` | str/null | 目标服务类型 | 邮件草稿衔接服务 |
| `topic_match_score` | int | 研究方向匹配分 | PubMed 临时评分 |
| `topic_match_reason` | str | 方向匹配理由 | 临时规则说明 |
| `publication_recency_score` | int | 发表时效分 | PubMed 临时评分 |
| `email_contactability_score` | int | 邮箱可联系分 | PubMed 临时评分 |
| `lead_score` | int | 总分 | PubMed 单源临时分 |
| `priority` | str | 优先级 | high / medium / low / unscored |
| `score_explanation` | str | 评分说明 | 当前为临时评分说明 |
| `funding_activity_score` | int/null | 基金活跃度分 | 当前未接基金源，通常为空 |
| `funding_activity_reason` | str | 基金分说明 | 当前说明基金源未接入 |
| `outsourcing_tendency_score` | int/null | 外包倾向分 | 当前未实现 |
| `official_scoring_status` | str | 正式评分状态 | 当前 `pending_multi_source_data` |

---

# 3. Crossref 字段

## 3.1 CrossrefSearchParams

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `doi` | str/null | DOI 查询 | DOI 优先 |
| `title` | str/null | 标题查询 | DOI 为空时使用 |
| `max_results` | int | 最大结果数 | 当前上限 20 |
| `raw_dir` | Path | raw 输出目录 | 默认 `data/raw/crossref` |
| `processed_dir` | Path | processed 输出目录 | 默认 `data/processed/crossref` |
| `query_label` | property | 文件名标签 | DOI 优先，其次 title |

## 3.2 CrossrefWork

用途：Crossref 清洗后的论文元数据。

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `source` | str | 数据源 | 固定 `crossref` |
| `crossref_id` | str | Crossref 内部标识 | 通常使用 DOI 或 URL |
| `doi` | str/null | DOI | 已标准化 |
| `title` | str | 标题 | 来自 Crossref |
| `abstract` | str | 摘要 | 可能为空 |
| `journal` | str | 期刊 / container title | 可能为空 |
| `publisher` | str | 出版社 | 可能为空 |
| `publication_date` | str | 出版日期 | 优先 print，再 online，再 created/deposited |
| `publication_year` | int/null | 出版年份 | 可能为空 |
| `authors` | list[str] | 作者列表 | Crossref 作者字段 |
| `funder_names` | list[str] | funder 名称 | 只表示 Crossref 元数据，不等于活跃基金 |
| `reference_count` | int/null | 参考文献数量 | Crossref 字段 |
| `is_referenced_by_count` | int/null | 被引用数量 | Crossref 字段 |
| `source_url` | str | 来源链接 | DOI 链接或 Crossref URL |
| `raw_record_path` | str/null | raw JSON 路径 | 用于追溯 |

---

# 4. OpenAlex 字段

## 4.1 SearchParams

用途：OpenAlex 查询输入。

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `query` | str | 检索关键词 | 不能为空 |
| `from_date` | str | 开始日期 | `YYYY-MM-DD` |
| `to_date` | str | 结束日期 | `YYYY-MM-DD` |
| `max_results` | int | 最大结果数 | 当前上限 20 |

## 4.2 PaperRecord

用途：OpenAlex 清洗后的论文记录。

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `openalex_id` | str | OpenAlex Work ID | 如 `https://openalex.org/W...` |
| `doi` | str/null | DOI | 已去前缀、转小写 |
| `title` | str | 标题 | title 或 display_name |
| `abstract` | str | 摘要 | 由 `abstract_inverted_index` 还原 |
| `publication_date` | str | 发表日期 | OpenAlex 字段 |
| `authors` | list[str] | 作者列表 | 从 authorships 提取 |
| `institutions` | list[str] | 机构列表 | 从 authorships 提取 |

---

# 5. 统一模型字段

## 5.1 EvidenceRecord

用途：记录某个字段来自哪里、证据是什么、置信度如何。

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `source_name` | str | 数据源名称 | pubmed / crossref / openalex |
| `source_type` | str | 来源对象类型 | 如 pubmed_lead / crossref_work |
| `source_id` | str | 来源对象 ID | PMID / DOI / OpenAlex ID / lead_id 等 |
| `source_url` | str | 来源链接 | 可点击追溯 |
| `retrieved_at` | str | 获取时间 | ISO 字符串 |
| `field_name` | str | 字段名 | 如 title / verified_email |
| `field_value` | str | 字段值 | list 会序列化为 JSON 字符串 |
| `confidence` | str | 置信度 | high / medium / unknown / temporary |
| `raw_record_path` | str/null | raw 文件路径 | 可为空 |
| `note` | str/null | 备注 | 可为空 |

## 5.2 UnifiedPaper

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `unified_id` | str | 统一论文 ID | DOI 优先生成 |
| `source_name` | str | 来源名称 | crossref / openalex 等 |
| `source_id` | str | 来源 ID | DOI / OpenAlex ID |
| `doi` | str/null | DOI | 可能为空 |
| `title` | str | 标题 | 统一字段 |
| `abstract` | str | 摘要 | 可能为空 |
| `journal` | str | 期刊 | OpenAlex 当前可能为空 |
| `publisher` | str/null | 出版社 | Crossref 有，OpenAlex 当前为空 |
| `publication_date` | str | 发表日期 | 统一字段 |
| `publication_year` | int/null | 发表年份 | 可能为空 |
| `authors` | list[str] | 作者 | 统一作者列表 |
| `organizations` | list[str] | 机构 | OpenAlex 映射 institutions |
| `source_url` | str | 来源链接 | DOI / OpenAlex URL |
| `raw_record_path` | str/null | raw 文件路径 | 可为空 |
| `evidence_records` | list[EvidenceRecord] | 字段证据 | 后续评分、报告使用 |

## 5.3 UnifiedResearcher

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `unified_id` | str | 统一研究人员 ID | 后续归并生成 |
| `full_name` | str | 姓名 | 不能只按姓名合并 |
| `emails` | list[str] | 邮箱列表 | 必须来自公开证据 |
| `organizations` | list[str] | 机构列表 | 可多机构 |
| `country` | str/null | 国家 | 可为空 |
| `source_ids` | dict[str,str] | 各来源 ID | 如 OpenAlex Author ID / ORCID |
| `merge_status` | str | 合并状态 | 默认 `not_merged` |
| `evidence_records` | list[EvidenceRecord] | 证据 | 后续归并依据 |

## 5.4 UnifiedOrganization

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `unified_id` | str | 统一机构 ID | 后续归并生成 |
| `name` | str | 机构名称 | 机构标准化后可更新 |
| `country` | str/null | 国家 | 可为空 |
| `source_ids` | dict[str,str] | 各来源 ID | 可放 OpenAlex institution ID 等 |
| `evidence_records` | list[EvidenceRecord] | 证据 | 来源和置信度 |

## 5.5 UnifiedFunding

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `unified_id` | str | 统一基金 ID | 后续生成 |
| `agency` | str | 资助机构 | NIH / NSF 等 |
| `project_title` | str | 项目名称 | 来自基金源 |
| `amount` | float/null | 金额 | 可能为空 |
| `fiscal_year` | int/null | 财年 | 可能为空 |
| `source_url` | str/null | 来源链接 | 可为空 |
| `evidence_records` | list[EvidenceRecord] | 证据 | 必须保留来源 |

## 5.6 UnifiedContact

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `unified_id` | str | 联系方式 ID | 后续生成 |
| `contact_type` | str | 联系方式类型 | 当前主要 email |
| `value` | str | 联系方式值 | 如邮箱 |
| `status` | str | 状态 | verified / missing / manual_review 等 |
| `source_url` | str | 来源链接 | 必须可追溯 |
| `evidence_records` | list[EvidenceRecord] | 证据 | 邮箱归属依据 |

---

# 6. 邮件草稿字段

## 6.1 EmailDraftInput

用途：生成邮件草稿前提供给模型的证据包。

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `lead_id` | str | Lead ID |
| `pi_full_name` | str | 候选 PI 姓名 |
| `recent_publication_title` | str | 近期论文标题 |
| `source_url` | str | 来源链接 |
| `target_service_type` | str | 目标服务类型 |
| `abstract` | str/null | 摘要 |
| `institution` | str/null | 机构 |
| `country` | str/null | 国家 |
| `verified_email` | str/null | 公开邮箱 |
| `email_status` | str/null | 邮箱状态 |
| `pmid` | str/null | PMID |
| `doi` | str/null | DOI |
| `matched_keywords` | list[str] | 匹配关键词 |
| `sender_name` | str/null | 发件人姓名占位 |
| `sender_title` | str/null | 发件人职位占位 |
| `organization_name` | str/null | 发件组织名称 |
| `service_context` | str/null | 服务说明上下文 |

## 6.2 EmailDraft

用途：生成后的英文邮件草稿，当前只用于人工审核，不发送。

| 字段 | 类型 | 含义 | 备注 |
| --- | --- | --- | --- |
| `lead_id` | str | 对应 Lead ID | |
| `subject` | str | 邮件标题 | 模型生成 |
| `body` | str | 邮件正文 | 模型生成 |
| `language` | str | 语言 | 当前 `en` |
| `draft_status` | str | 草稿状态 | 当前默认 `review_pending` |
| `generated_at` | str | 生成时间 | ISO 字符串 |
| `model_name` | str | 使用模型名 | 可能为 unknown |
| `source_paper_title` | str | 来源论文标题 | |
| `source_pmid` | str/null | 来源 PMID | |
| `doi` | str/null | DOI | |
| `source_url` | str | 来源链接 | |
| `target_service_type` | str | 目标服务类型 | |
| `human_reviewer` | str/null | 人工审核人 | 当前可为空 |
| `reviewed_at` | str/null | 审核时间 | 当前可为空 |
| `recipient_name` | str/null | 收件人姓名 | 候选 PI |
| `verified_email` | str/null | 收件邮箱 | 可能为空 |
| `email_status` | str/null | 邮箱状态 | |
| `evidence` | dict | 生成草稿使用的证据 | 不应含 API Key |
| `warnings` | list[str] | 风险提示 | 如 missing_verified_email |
| `can_send` | bool | 是否可发送 | 当前固定 false |

---

# 7. Agent / Tool 字段

## 7.1 当前 Tool 列表

| Tool | 用途 | 当前边界 |
| --- | --- | --- |
| `search_pubmed` | 检索 PubMed 并生成 PubMed Lead | 可生成临时 Lead 和临时评分，不发邮件 |
| `search_crossref` | 查询 Crossref DOI / 出版元数据 | 不生成 Lead，不判断活跃基金 |
| `search_openalex` | 查询 OpenAlex Works 元数据 | 不生成 Lead，不评分 |
| `generate_email_draft` | 生成英文邮件草稿 | 不发送邮件 |

## 7.2 ToolResult

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `success` | bool | Tool 是否成功 |
| `source` | str | 来源模块 |
| `data` | dict | Tool 返回数据 |
| `error_code` | str/null | 错误代码 |
| `error_message` | str/null | 错误信息 |
| `errors` | list[dict] | 多错误列表 |

## 7.3 ToolDefinition

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `name` | str | Tool 名称 |
| `description` | str | Tool 说明 |
| `input_schema` | dict | 暴露给模型的参数 schema |
| `effect` | str | 工具影响类型，当前支持 read/write/execute/external |
| `handler` | callable | 实际执行函数 |

## 7.4 ToolContext

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `workspace` | str/null | 工作区 |
| `task_id` | str/null | 任务 ID |
| `run_id` | str/null | 运行 ID |
| `identity` | str/null | 调用身份 |
| `idempotency_key` | str/null | 幂等键 |

## 7.5 ModelUsage / ModelReply

| 对象 | 字段 | 类型 | 含义 |
| --- | --- | --- | --- |
| ModelUsage | `input_tokens` | int/null | 输入 token |
| ModelUsage | `output_tokens` | int/null | 输出 token |
| ModelUsage | `total_tokens` | int/null | 总 token |
| ModelReply | `content` | str/null | 模型文本回复 |
| ModelReply | `tool_calls` | list[dict] | 模型请求调用的工具 |
| ModelReply | `finish_reason` | str | 结束原因 |
| ModelReply | `usage` | ModelUsage/null | token 使用 |
| ModelReply | `model` | str/null | 模型名称 |

---

# 8. AI Usage 字段

用途：记录每次模型调用，不记录 API Key，不保存完整 prompt。

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `usage_id` | str | 使用记录 ID |
| `account_alias` | str | 账号别名 |
| `provider` | str | 模型供应商类型 |
| `called_at` | str | 调用时间 |
| `feature_module` | str | 功能模块，如 agent_reasoning / email_draft |
| `model_name` | str/null | 模型名称 |
| `input_tokens` | int/null | 输入 token |
| `output_tokens` | int/null | 输出 token |
| `total_tokens` | int/null | 总 token |
| `estimated_cost` | float/null | 预估费用，未知则为空 |
| `currency` | str/null | 币种 |
| `pricing_config_version` | str | 价格配置版本 |
| `status` | str | success / failed |
| `error_type` | str/null | 错误类型 |
| `error_message` | str/null | 错误信息 |
| `task_id` | str/null | 任务 ID |
| `lead_id` | str/null | Lead ID |
| `started_at` | str | 开始时间 |
| `finished_at` | str | 结束时间 |
| `latency_ms` | int | 耗时毫秒 |

保存位置：

```text
data/processed/ai_usage/ai_usage_YYYYMMDD.jsonl
```

---

# 9. Run Result / Run Report 字段

## 9.1 PubMedRunResult

| 字段 | 含义 |
| --- | --- |
| `task_id` | PubMed 任务 ID |
| `status` | success / failed / partial_failure |
| `search_params` | PubMedSearchParams |
| `pmids` | PMID 列表 |
| `papers` | PubMedPaper 列表 |
| `leads` | PubMedLead 列表 |
| `raw_paths` | raw 文件路径对象 |
| `processed_paths` | processed 文件路径对象 |
| `raw_files` | raw 文件路径 dict |
| `processed_files` | processed 文件路径 dict |
| `run_report_path` | run report 路径 |
| `run_report` | run report 内容 |
| `errors` | 错误列表 |
| `started_at` | 开始时间 |
| `finished_at` | 结束时间 |

## 9.2 CrossrefRunResult

| 字段 | 含义 |
| --- | --- |
| `task_id` | Crossref 任务 ID |
| `status` | success / failed / partial_failure |
| `search_params` | CrossrefSearchParams |
| `works` | CrossrefWork 列表 |
| `raw_paths` | raw 文件路径对象 |
| `processed_paths` | processed 文件路径对象 |
| `raw_files` | raw 文件路径 dict |
| `processed_files` | processed 文件路径 dict |
| `run_report_path` | run report 路径 |
| `run_report` | run report 内容 |
| `errors` | 错误列表 |
| `started_at` | 开始时间 |
| `finished_at` | 结束时间 |

## 9.3 OpenAlexRunResult

| 字段 | 含义 |
| --- | --- |
| `task_id` | OpenAlex 任务 ID |
| `status` | success / failed / partial_failure |
| `search_params` | SearchParams |
| `works` | PaperRecord 列表 |
| `unified_papers` | UnifiedPaper 列表 |
| `output_paths` | 输出路径对象 |
| `raw_files` | raw 文件路径 dict |
| `processed_files` | processed 文件路径 dict |
| `run_report_path` | run report 路径 |
| `run_report` | run report 内容 |
| `errors` | 错误列表 |
| `started_at` | 开始时间 |
| `finished_at` | 结束时间 |

---

# 10. CSV 导出字段

## 10.1 PubMed papers CSV

```text
Source
PMID
DOI
Title
Abstract
Journal
Publication_Date
Publication_Year
Article_Types
MeSH_Terms
Keywords
Authors
Affiliations
Source_URL
Raw_Record_Path
```

## 10.2 PubMed leads CSV

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
Country_Source
Raw_Affiliation
Recent_Publication_Title
Abstract
Journal
Publication_Year
PMID
DOI
Author_Role
Matched_Keywords
Target_Service_Type
Topic_Match_Score
Publication_Recency_Score
Email_Contactability_Score
Lead_Score
Priority
Score_Explanation
Data_Quality
Merge_Status
Merge_Reason
Manual_Review_Required
Funding_Activity_Score
Funding_Activity_Reason
Outsourcing_Tendency_Score
Official_Scoring_Status
Source_Links
Notes
```

## 10.3 Crossref works CSV

```text
Source
Crossref_ID
DOI
Title
Abstract
Journal
Publisher
Publication_Date
Publication_Year
Authors
Funder_Names
Reference_Count
Is_Referenced_By_Count
Source_URL
Raw_Record_Path
```

## 10.4 OpenAlex processed CSV

```text
openalex_id
doi
title
abstract
publication_date
authors
institutions
```

---

# 11. 配置字段

## 11.1 AppConfig

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `app_env` | str | 运行环境 |
| `openalex_base_url` | str | OpenAlex API 地址 |
| `openalex_user_agent` | str | OpenAlex User-Agent |
| `crossref_base_url` | str | Crossref API 地址 |
| `crossref_user_agent` | str | Crossref User-Agent |
| `crossref_mailto` | str/null | Crossref polite mailto |
| `pubmed_esearch_url` | str | PubMed ESearch URL |
| `pubmed_efetch_url` | str | PubMed EFetch URL |
| `pubmed_user_agent` | str | PubMed User-Agent |
| `ncbi_tool` | str | NCBI tool 名称 |
| `ncbi_email` | str/null | NCBI email |
| `ncbi_api_key` | str/null | NCBI API Key，不提交 |
| `openai_provider` | str | 模型供应商类型 |
| `openai_account_alias` | str | 模型账号别名 |
| `openai_api_key` | str/null | 模型 API Key，不提交 |
| `openai_base_url` | str/null | 模型 API 地址 |
| `openai_model` | str/null | 默认模型 |
| `openai_fallback_model` | str/null | 备用模型 |
| `agent_default_model` | str/null | Agent 默认模型 |
| `email_draft_default_model` | str/null | 邮件草稿默认模型 |
| `ai_usage_dir` | Path | AI usage 保存目录 |
| `token_warning_threshold` | int/null | token 提醒阈值，当前仅预留 |
| `cost_warning_threshold` | float/null | 费用提醒阈值，当前仅预留 |
| `ai_pricing_config_version` | str | 模型价格配置版本 |
| `request_timeout_seconds` | int | HTTP 超时时间 |
| `retry_count` | int | 重试次数 |
| `raw_data_dir` | Path | raw 根目录 |
| `processed_data_dir` | Path | processed 根目录 |

## 11.2 常用环境变量

```text
NCBI_TOOL
NCBI_EMAIL
NCBI_API_KEY
CROSSREF_BASE_URL
CROSSREF_USER_AGENT
CROSSREF_MAILTO
OPENAI_API_KEY
OPENAI_BASE_URL
OPENAI_MODEL
OPENAI_FALLBACK_MODEL
OPENAI_PROVIDER
OPENAI_ACCOUNT_ALIAS
AGENT_DEFAULT_MODEL
EMAIL_DRAFT_DEFAULT_MODEL
AI_USAGE_DIR
TOKEN_WARNING_THRESHOLD
COST_WARNING_THRESHOLD
AI_PRICING_CONFIG_VERSION
```

---

# 12. 当前未落地但后续会新增的字段方向

后续阶段可能新增：

- NIH / NSF 基金字段：`grant_id`、`agency`、`project_title`、`amount`、`fiscal_year`、`project_start`、`project_end`；
- Researcher 正式归并字段：`orcid`、`openalex_author_id`、`merge_confidence`；
- 正式评分字段：`funding_activity_score`、`research_direction_score`、`publication_recency_score`、`outsourcing_tendency_score`、`official_total_score`；
- 邮件审核字段：`review_status`、`approved_by`、`approved_at`、`send_status`；
- 数据库字段：`created_at`、`updated_at`、`deleted_at`、`tenant_id`、`owner_id` 等。

这些字段目前不能当作已经完成。
