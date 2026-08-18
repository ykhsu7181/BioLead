# PubMed 第一轮阶段 5：PubMed XML 解析

日期：2026-08-17  
项目：ScholarLead Agent  
阶段：Stage 5 - PubMed XML 解析

## 1. 阶段目标

本阶段实现 PubMed EFetch XML 到结构化论文数据的解析。

本阶段只负责：

- 解析 PubMed XML。
- 提取论文核心字段。
- 提取作者顺序和 affiliation 文本。
- 标准化 DOI。
- 处理多段摘要。
- 处理缺失字段。
- 生成 PubMed 来源链接。

本阶段不负责：

- 调用 PubMed API。
- 保存 raw 文件。
- 从 affiliation 中提取邮箱。
- 生成 Lead。
- 论文去重。
- 国家和机构识别。
- 评分。
- processed JSON / CSV 导出。

## 2. 本阶段新增和修改

新增代码：

```text
src/scholarlead_agent/pubmed_parser.py
```

修改模型：

```text
src/scholarlead_agent/pubmed_models.py
```

新增测试：

```text
tests/fixtures/pubmed_efetch_response.xml
tests/test_pubmed_parser.py
```

## 3. 新增数据模型

新增 `PubMedAuthor`：

```text
full_name
last_name
fore_name
initials
author_position
is_last_author
affiliations
```

新增 `PubMedPaper`：

```text
source
pmid
doi
title
abstract
journal
publication_date
publication_year
article_types
mesh_terms
keywords
authors
affiliations
source_url
raw_record_path
```

## 4. Parser 能力

新增函数：

```text
parse_pubmed_xml(raw_xml, raw_record_path=None)
normalize_pubmed_doi(value)
```

`parse_pubmed_xml`：

- 输入 PubMed EFetch XML 字符串。
- 输出 `list[PubMedPaper]`。
- XML 格式错误时抛出 `ValueError("PubMed XML is malformed")`。

`normalize_pubmed_doi`：

- 去除 `https://doi.org/`。
- 去除 `http://doi.org/`。
- 去除 `doi:`。
- 去除首尾空格。
- 转换为小写。
- 空值返回 `None`。

## 5. 已支持字段解析

论文层面：

- PMID。
- DOI。
- 标题。
- 摘要。
- 期刊。
- 发表日期。
- 发表年份。
- 文章类型。
- MeSH 主题词。
- 关键词。
- PubMed 来源链接。
- raw XML 文件路径。

作者层面：

- 姓。
- 名。
- initials。
- full name。
- 作者顺序。
- 是否最后一作者。
- affiliation 文本。

## 6. 缺失字段处理

当前规则：

- 缺失 DOI：`doi = None`。
- 缺失摘要：`abstract = ""`。
- 缺失 MeSH：`mesh_terms = []`。
- 缺失关键词：`keywords = []`。
- 缺失文章类型：`article_types = []`。
- 缺失 affiliation：`affiliations = []`。
- 缺失日期但有年份：`publication_date = "YYYY"`。
- 无法识别年份：`publication_year = None`。

缺失字段不会导致整个解析流程崩溃。

## 7. Affiliation 边界

本阶段只保留 affiliation 原文。

本阶段不从 affiliation 中提取邮箱，也不识别国家和机构。

后续阶段：

- 阶段 6：邮箱提取与邮箱证据。
- 阶段 10：国家与机构基础识别。

## 8. 测试覆盖

新增 `tests/test_pubmed_parser.py`，覆盖：

- 解析 PMID。
- 解析 DOI 并标准化。
- 解析标题。
- 解析多段摘要。
- 解析期刊。
- 解析发表日期和发表年份。
- 解析文章类型。
- 解析 MeSH。
- 解析关键词。
- 解析作者顺序。
- 识别最后一作者。
- 保留 affiliation。
- 处理缺失 DOI。
- 处理缺失摘要。
- 处理 collective author。
- 拒绝 malformed XML。

测试 fixture：

```text
tests/fixtures/pubmed_efetch_response.xml
```

测试中不访问真实网络。

## 9. 当前测试结果

测试命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

当前结果：

```text
47 passed
```

## 10. 阶段 5 验收结论

阶段 5 已完成。

已经得到：

- PubMed XML parser。
- PubMed paper 数据模型。
- PubMed author 数据模型。
- DOI 标准化。
- 多段摘要合并。
- 作者顺序解析。
- 最后一作者识别。
- affiliation 原文保留。
- 缺失字段容错。
- malformed XML 错误处理。
- parser 测试 fixture。
- 完整 pytest 通过。

尚未实现：

- 邮箱提取。
- 邮箱来源证据。
- 论文去重。
- Lead 生成。
- 国家和机构识别。
- 关键词匹配。
- 临时评分。
- processed 导出。

可以进入阶段 6：

```text
邮箱提取与邮箱证据
```

阶段 6 建议重点实现：

- `src/scholarlead_agent/pubmed_leads.py`
- 从 affiliation 中提取邮箱。
- 校验邮箱格式。
- 记录邮箱来源链接。
- 记录 matched affiliation。
- 标记邮箱和作者匹配置信度。
- 不猜测邮箱。
