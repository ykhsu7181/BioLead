# 阶段21B：多源统一数据模型最小版

## 本阶段目标

在继续接入 OpenAlex、基金源和 ORCID 之前，先建立一层最小统一数据模型，减少后续多源归并返工。

本阶段只做模型和转换，不替换 PubMed / Crossref / OpenAlex 已有导出，不做数据库，不做正式合并算法，不做正式评分。

## 已完成内容

1. 新增统一模型：
   - `EvidenceRecord`
   - `UnifiedPaper`
   - `UnifiedResearcher`
   - `UnifiedOrganization`
   - `UnifiedFunding`
   - `UnifiedContact`
2. 新增转换函数：
   - `evidence_from_pubmed_lead`
   - `crossref_work_to_unified_paper`
   - `openalex_record_to_unified_paper`
3. PubMed Lead 可以转换出基础 Evidence。
4. Crossref Work 可以转换成 UnifiedPaper。
5. OpenAlex 旧 `PaperRecord` 可以转换成 UnifiedPaper 草案。
6. 原有 PubMed / Crossref / OpenAlex 导出逻辑未替换。

## 新增文件

```text
src/scholarlead_agent/unified_models.py
src/scholarlead_agent/unified_converters.py
tests/test_unified_models.py
tests/test_unified_converters.py
docs/pubmed_stage21b_unified_models.md
```

## EvidenceRecord 字段

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

## 当前转换规则

### PubMed Lead -> Evidence

转换字段包括：

- `pi_full_name`
- `verified_email`
- `email_status`
- `institution`
- `country`
- `recent_publication_title`
- `pmid`
- `doi`
- `author_role`
- `raw_affiliation`
- `matched_keywords`
- `target_service_type`
- `lead_score`
- `priority`

说明：

- 没有 verified email 时，不生成 `verified_email` evidence；
- `lead_score` 和 `priority` 置信度标记为 `temporary`；
- 不把 PubMed 临时分说成正式四维评分。

### Crossref Work -> UnifiedPaper

映射字段包括：

- DOI
- title
- abstract
- journal
- publisher
- publication_date
- publication_year
- authors
- funder_names
- reference_count
- is_referenced_by_count

说明：

- `funder_names` 只是 Crossref 返回的 funder 元数据；
- 不表示活跃基金；
- 不直接生成 Lead。

### OpenAlex PaperRecord -> UnifiedPaper

映射字段包括：

- OpenAlex ID
- DOI
- title
- abstract
- publication_date
- publication_year
- authors
- institutions

说明：

- 当前 OpenAlex 旧模型没有 journal / publisher，统一模型里先留空；
- 21C 再正式整理 OpenAlex Service / Tool。

## 不做范围

本阶段不做：

- 大规模迁移历史文件；
- 数据库；
- 正式 Researcher 合并；
- 正式 Organization 合并；
- 正式评分；
- UI 大改；
- 邮件发送。

## 测试覆盖

新增测试覆盖：

- `EvidenceRecord` 字段和序列化；
- 统一模型序列化；
- PubMed Lead 转 Evidence；
- 缺失邮箱处理；
- Crossref Work 转 UnifiedPaper；
- Crossref funder evidence 保留但不推断；
- OpenAlex PaperRecord 转 UnifiedPaper 草案。

## 已知限制

1. 统一模型目前是转换层，没有替换现有业务输出。
2. `UnifiedResearcher` / `UnifiedOrganization` 当前只是壳模型，正式归并在 21E。
3. `UnifiedFunding` 当前只是壳模型，真实基金源在 21D。
4. 当前没有数据库保存统一模型。
5. 当前没有 UI 展示统一模型。

## 阶段验收

阶段 21B 已达到 v2.3 最小验收要求：

- PubMed Lead 可转换出基础 Evidence；
- Crossref Work 可转换出 UnifiedPaper；
- OpenAlex 旧模块可映射到 UnifiedPaper 草案；
- 不破坏已有导出；
- 测试中不访问真实网络。
