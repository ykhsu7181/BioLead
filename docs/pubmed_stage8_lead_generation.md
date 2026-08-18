# PubMed 第一轮阶段 8：Lead 生成

日期：2026-08-17  
项目：ScholarLead Agent  
阶段：Stage 8 - Lead 生成

## 1. 阶段目标

本阶段实现从 PubMed 论文、作者和邮箱证据生成候选客户线索。

本阶段只负责：

- 从 `PubMedPaper` 生成候选 Lead。
- 优先使用有邮箱证据的作者。
- high 置信邮箱生成可联系 Lead。
- medium 置信邮箱生成需要人工确认的 Lead。
- 无邮箱时使用最后一作者作为 PI 候选。
- 明确最后一作者不是“已确认 PI”。
- 保留 PubMed 来源链接。

本阶段不负责：

- Lead 去重。
- 国家和机构基础识别。
- 关键词匹配。
- 临时评分。
- processed JSON / CSV 导出。
- 邮件草稿生成。
- 邮件发送。

## 2. 本阶段新增和修改

修改模型：

```text
src/scholarlead_agent/pubmed_models.py
```

修改代码：

```text
src/scholarlead_agent/pubmed_leads.py
```

修改测试：

```text
tests/test_pubmed_leads.py
```

## 3. 新增数据模型

新增 `PubMedLead`：

```text
lead_id
pi_full_name
verified_email
email_status
email_source_url
email_source_type
name_email_match_confidence
institution
country
country_confidence
recent_publication_title
abstract
journal
publication_year
pmid
doi
author_role
source_links
data_quality
manual_review_required
notes
```

## 4. 新增函数

新增：

```text
build_leads_from_papers(papers)
build_leads_from_paper(paper)
```

`build_leads_from_papers`：

- 输入多篇 `PubMedPaper`。
- 返回候选 `PubMedLead` 列表。
- 不做 Lead 去重。

`build_leads_from_paper`：

- 输入单篇 `PubMedPaper`。
- 先提取邮箱证据。
- 如果存在可用邮箱证据，生成邮箱作者 Lead。
- 如果没有可用邮箱，使用最后一作者生成 PI 候选 Lead。
- 如果没有作者且没有邮箱，不生成 Lead。

## 5. Lead 生成优先级

当前生成顺序：

```text
1. 有 high 置信邮箱的作者
2. 有 medium 置信邮箱的作者
3. 无邮箱时的最后一作者
4. 无作者且无邮箱时不生成 Lead
```

说明：

- high 置信邮箱：`manual_review_required = false`。
- medium 置信邮箱：`manual_review_required = true`。
- 最后一作者：只作为 `candidate_pi_last_author`，不是已确认 PI。

## 6. Author Role

当前支持：

```text
email_author
email_author_needs_review
candidate_pi_last_author
candidate_author
candidate
```

阶段 8 实际主要使用：

- `email_author`
- `candidate_pi_last_author`

后续阶段可继续细化通讯作者、第一作者、共同作者等角色。

## 7. 缺省字段处理

阶段 8 暂不做国家识别，因此：

```text
country = unknown
country_confidence = pending
```

阶段 8 暂不做评分，因此：

- 不输出 `lead_score`。
- 不输出 `priority`。
- 不输出 `score_explanation`。

这些字段留到后续阶段。

## 8. 不夸大能力

本阶段生成的是：

```text
PI / 通讯作者候选 Lead
```

不是：

```text
已确认 PI
已确认客户
已验证销售线索
```

尤其是无邮箱最后一作者，只能标记为：

```text
candidate_pi_last_author
```

并且：

```text
manual_review_required = true
```

## 9. 测试覆盖

新增测试覆盖：

- high 置信邮箱作者生成可联系 Lead。
- medium 置信邮箱作者生成需要人工确认的 Lead。
- 无邮箱时最后一作者生成 PI 候选 Lead。
- 无作者且无邮箱时不生成 Lead。
- 多篇 paper 可合并生成 Lead 列表。
- Lead 保留 PubMed source URL。
- Lead 保留论文标题、摘要、期刊、年份、PMID、DOI。

## 10. 当前测试结果

测试命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

当前结果：

```text
65 passed
```

## 11. 阶段 8 验收结论

阶段 8 已完成。

已经得到：

- PubMed Lead 数据模型。
- 单篇 paper 到 Lead 的生成函数。
- 多篇 papers 到 Lead 的生成函数。
- high 邮箱证据 Lead。
- medium 邮箱证据 Lead。
- 无邮箱最后一作者候选 Lead。
- 人工审核标记。
- 来源链接保留。
- 完整测试覆盖。

尚未实现：

- Lead 去重。
- 国家和机构基础识别。
- 关键词匹配。
- 临时评分。
- processed JSON / CSV 导出。
- 端到端 CLI 串联。

可以进入阶段 9：

```text
Lead 去重与人工审核标记
```

阶段 9 建议重点实现：

- verified_email 相同的 Lead 合并。
- 同一 PMID + 同一作者名的 Lead 合并。
- 姓名相同 + 机构相同标记 candidate，不强制合并。
- 只有姓名相同不合并。
