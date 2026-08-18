# PubMed 第一轮阶段 7：论文去重

日期：2026-08-17  
项目：ScholarLead Agent  
阶段：Stage 7 - 论文去重

## 1. 阶段目标

本阶段实现 PubMed 论文级去重。

本阶段只负责：

- 对已解析出的 `PubMedPaper` 列表去重。
- 优先按 DOI 去重。
- 没有 DOI 时按 PMID 去重。
- 暴露去重依据。
- 保留首次出现的记录。
- 不根据标题相似度合并。

本阶段不负责：

- 调用 PubMed API。
- 保存 raw 文件。
- 删除 raw 文件。
- 提取邮箱。
- 生成 Lead。
- Lead 去重。
- 国家和机构识别。
- 临时评分。
- processed 导出。

## 2. 本阶段修改内容

修改代码：

```text
src/scholarlead_agent/pubmed_parser.py
```

修改测试：

```text
tests/test_pubmed_parser.py
```

## 3. 新增函数

新增：

```text
deduplicate_pubmed_papers(papers)
get_pubmed_paper_dedup_key(paper)
```

`get_pubmed_paper_dedup_key(paper)` 返回：

```text
("doi", normalized_doi)
```

或：

```text
("pmid", pmid)
```

如果 DOI 和 PMID 都没有，则返回：

```text
None
```

## 4. 去重规则

规则顺序：

```text
1. 有 DOI：按 DOI 去重
2. 没有 DOI：按 PMID 去重
3. 没有 DOI 且没有 PMID：不自动合并
```

DOI 会再次经过标准化：

- 去除 `https://doi.org/`
- 去除 `http://doi.org/`
- 去除 `doi:`
- 去除首尾空格
- 转小写

## 5. 保留策略

如果出现重复记录：

```text
保留第一次出现的记录
跳过后续重复记录
```

原因：

- 第一轮先保持逻辑简单可复现。
- 不在本阶段做复杂字段合并。
- 不冒险覆盖已解析数据。

## 6. 不做标题相似合并

本阶段明确不根据标题相似度合并论文。

例如：

```text
title 相同
DOI 不同
PMID 不同
```

处理结果：

```text
保留两条
```

原因：

- 标题相似或相同不一定是同一篇论文。
- 可能存在 corrigendum、preprint、正式发表版本、会议摘要等情况。
- 第一轮不做复杂文献实体归并。

## 7. Raw 数据不受影响

论文去重只作用于解析后的 `PubMedPaper` 列表。

不会删除：

```text
data/raw/pubmed/*_esearch.json
data/raw/pubmed/*_efetch.xml
data/raw/pubmed/*_request_meta.json
```

raw 数据必须继续完整保留，方便后续重新清洗。

## 8. 测试覆盖

新增测试覆盖：

- 去重 key 优先使用 DOI。
- 没有 DOI 时使用 PMID。
- 相同 DOI 只保留第一条。
- 没有 DOI 且 PMID 相同，只保留第一条。
- 标题相同但 DOI 不同，不合并。
- DOI 和 PMID 都缺失，不自动合并。

## 9. 当前测试结果

测试命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

当前结果：

```text
60 passed
```

## 10. 阶段 7 验收结论

阶段 7 已完成。

已经得到：

- PubMed paper 去重函数。
- PubMed paper 去重依据函数。
- DOI 优先去重。
- 无 DOI 时按 PMID 去重。
- 标题相似不强制合并。
- 无 DOI/PMID 时不自动合并。
- 完整测试覆盖。

尚未实现：

- Lead 生成。
- Lead 去重。
- 国家和机构识别。
- 关键词匹配。
- 临时评分。
- processed JSON / CSV 导出。
- 端到端 CLI 串联。

可以进入阶段 8：

```text
Lead 生成
```

阶段 8 建议重点实现：

- 从 `PubMedPaper` 和 `PubMedEmailEvidence` 生成候选 Lead。
- 有 high 置信邮箱的作者优先。
- medium 置信邮箱标记需要人工确认。
- 无邮箱时最后一作者可作为 PI 候选。
- 不把最后一作者写成已确认 PI。
