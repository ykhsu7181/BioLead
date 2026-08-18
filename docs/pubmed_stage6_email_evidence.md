# PubMed 第一轮阶段 6：邮箱提取与邮箱证据

日期：2026-08-17  
项目：ScholarLead Agent  
阶段：Stage 6 - 邮箱提取与邮箱证据

## 1. 阶段目标

本阶段实现从 PubMed affiliation 文本中提取邮箱，并为每个邮箱保留来源证据和作者匹配置信度。

本阶段只负责：

- 从 PubMed affiliation 文本中提取邮箱。
- 校验邮箱格式。
- 标准化邮箱为小写。
- 记录邮箱来源类型。
- 记录 PubMed 来源链接。
- 记录邮箱所在 affiliation 原文。
- 记录匹配作者姓名。
- 记录邮箱和作者的匹配置信度。
- 无邮箱时标记 missing。
- 无效邮箱格式时标记 invalid_format。

本阶段不负责：

- 猜测邮箱。
- 根据姓名拼接邮箱。
- 根据机构域名推断邮箱。
- 访问外部网页补充邮箱。
- 生成 Lead。
- Lead 去重。
- 国家和机构识别。
- 临时评分。
- 邮件草稿生成。
- 邮件发送。

## 2. 本阶段新增和修改

新增代码：

```text
src/scholarlead_agent/pubmed_leads.py
```

修改模型：

```text
src/scholarlead_agent/pubmed_models.py
```

新增测试：

```text
tests/test_pubmed_leads.py
```

## 3. 新增数据模型

新增 `PubMedEmailEvidence`：

```text
email
email_status
email_source_type
email_source_url
matched_author_name
matched_affiliation
name_email_match_confidence
email_reason
```

## 4. 新增函数

新增函数：

```text
extract_email_evidence_from_paper(paper)
extract_valid_emails_from_text(text)
is_valid_email(value)
```

`extract_email_evidence_from_paper`：

- 输入：`PubMedPaper`
- 输出：`list[PubMedEmailEvidence]`
- 只扫描 `paper.authors[*].affiliations` 和必要时的 `paper.affiliations`
- 不访问网络
- 不生成 Lead

## 5. 邮箱来源规则

邮箱只允许来自：

```text
PubMed affiliation
```

邮箱来源字段固定为：

```text
email_source_type = pubmed_affiliation
```

来源链接使用：

```text
https://pubmed.ncbi.nlm.nih.gov/{pmid}/
```

## 6. 邮箱状态

当前支持状态：

| 状态 | 含义 |
| --- | --- |
| `verified_from_pubmed_affiliation` | 邮箱格式有效，来自 PubMed affiliation |
| `needs_review` | 邮箱有效，但无法明确绑定到具体作者 |
| `missing` | affiliation 中未发现邮箱 |
| `invalid_format` | affiliation 中出现疑似邮箱文本，但格式不完整 |

## 7. 作者匹配置信度

当前支持置信度：

| 置信度 | 规则 |
| --- | --- |
| `high` | 邮箱出现在单一作者自己的 affiliation 中 |
| `medium` | 多个作者共享同一 affiliation，邮箱可见但人员归属不唯一 |
| `needs_review` | 有邮箱，但没有可绑定作者 |
| `missing` | 没有邮箱 |
| `invalid_format` | 邮箱格式无效 |

## 8. 无邮箱规则

如果一篇论文的 affiliation 中没有任何邮箱，返回一条 missing 证据：

```text
email = None
email_status = missing
email_source_type = pubmed_affiliation
email_source_url = PubMed paper URL
matched_author_name = None
matched_affiliation = None
name_email_match_confidence = missing
email_reason = source_data_not_provided
```

这样后续导出时不会把“没查到邮箱”和“字段漏处理”混在一起。

## 9. 不猜测邮箱原则

本阶段明确禁止：

- 用作者姓名拼接邮箱。
- 用机构域名猜邮箱。
- 用常见格式生成邮箱。
- 从网页、PDF 或搜索引擎补邮箱。
- 把无证据邮箱写成 verified email。

## 10. 测试覆盖

新增 `tests/test_pubmed_leads.py`，覆盖：

- 有效邮箱提取。
- 邮箱小写标准化。
- 重复邮箱去重。
- 不完整邮箱格式拒绝。
- 单作者 affiliation 标记 high。
- 多作者共享 affiliation 标记 medium。
- 无邮箱标记 missing。
- 无效邮箱标记 invalid_format。
- 无作者但 affiliation 有邮箱时标记 needs_review。

测试中不访问真实网络。

## 11. 当前测试结果

测试命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

当前结果：

```text
54 passed
```

## 12. 阶段 6 验收结论

阶段 6 已完成。

已经得到：

- PubMed affiliation 邮箱提取。
- 邮箱格式校验。
- 邮箱小写标准化。
- 邮箱来源链接。
- 邮箱所在 affiliation 原文。
- 邮箱和作者匹配置信度。
- missing 状态。
- invalid_format 状态。
- needs_review 状态。
- 完整单元测试。

尚未实现：

- Lead 生成。
- Lead 去重。
- 国家和机构基础识别。
- 关键词匹配。
- 临时评分。
- processed 导出。
- 邮件草稿。
- 邮件发送。

可以进入阶段 7：

```text
论文去重
```

阶段 7 建议重点实现：

- DOI 优先去重。
- 没有 DOI 时使用 PMID 去重。
- 不根据标题相似度强行合并。
- 保留去重依据。
- 不删除 raw 文件。
