# PubMed 阶段 11：关键词匹配与服务类型标记

## 1. 本阶段目标

阶段 11 的目标是使用确定性 Python 规则，从 PubMed 论文信息中判断用户 query 是否命中论文主题，并给 Lead 补充后续评分需要的基础字段。

本阶段补齐字段：

```text
matched_keywords
target_service_type
topic_match_score
topic_match_reason
```

## 2. 本阶段不做什么

本阶段只做关键词匹配和服务类型标记，不做后续功能：

```text
不做 PubMed 单源总评分
不做 priority 分级
不做 publication_recency_score
不做 email_contactability_score
不做 funding / outsourcing 正式评分
不接入 LLM
不接入 Agent Loop
不接入 Crossref
不访问真实网络
不生成或发送邮件
```

## 3. 涉及文件

### 3.1 新增文件

```text
src/scholarlead_agent/pubmed_scoring.py
```

职责：

```text
1. 规范化关键词
2. 从 query 中提取 phrase / token
3. 在 title / abstract / MeSH / keywords 中查找命中
4. 写入 target_service_type
5. 生成 topic_match_score
6. 生成 topic_match_reason
7. 给 PubMedLead 批量补齐关键词匹配字段
```

### 3.2 修改文件

```text
src/scholarlead_agent/pubmed_models.py
```

为 `PubMedLead` 增加默认字段：

```text
matched_keywords = []
target_service_type = None
topic_match_score = 0
topic_match_reason = No matched keywords. default rule / pending client keyword hierarchy.
```

这些字段都有默认值，不影响之前阶段已有的 Lead 构造逻辑。

### 3.3 新增测试文件

```text
tests/test_pubmed_scoring.py
```

## 4. 新增核心函数

```python
normalize_keywords(...)
```

规范化关键词，统一小写、去空格、按分隔符拆分、去重。

```python
extract_query_terms(...)
```

从用户 query 中提取匹配项，优先保留多词短语，再补充有效 token。

```python
find_matched_keywords(...)
```

在 title、abstract、MeSH、keywords 中查找 query 命中。

```python
calculate_topic_match_score(...)
```

根据命中关键词数量生成阶段 11 的临时主题匹配分。

```python
build_topic_match_reason(...)
```

生成可解释的匹配原因。

```python
match_pubmed_keywords(...)
```

统一入口：输入 query、论文文本字段和 service_type，输出关键词匹配结果。

```python
match_pubmed_paper_keywords(...)
```

针对一篇 PubMedPaper 进行关键词匹配。

```python
enrich_lead_keyword_match(...)
```

给单条 PubMedLead 补齐阶段 11 字段。

```python
enrich_leads_keyword_match(...)
```

批量给 PubMedLead 补齐阶段 11 字段。

## 5. 匹配规则

第一版采用简单、稳定、可测试的确定性规则：

```text
1. 大小写不敏感
2. 去除多余空格
3. 支持逗号、分号、斜杠、竖线、加号、换行拆分 query
4. 多词短语优先匹配
5. 短语已命中时，不重复输出短语内部 token
6. title / abstract / MeSH / keywords 均可作为命中来源
7. 不命中时保持 matched_keywords = []
8. 不使用 LLM 推断研究方向
```

示例：

```text
query = spatial transcriptomics
title = Spatial transcriptomics reveals tumor regions
```

结果：

```text
matched_keywords = ["spatial transcriptomics"]
topic_match_score = 60
```

## 6. topic_match_score 第一版规则

阶段 11 的 `topic_match_score` 只是主题匹配分，不是最终 Lead 总分。

```text
0 个命中  -> 0
1 个命中  -> 60
2 个命中  -> 80
3 个及以上命中 -> 100
query_terms 全部命中 -> 100
```

后续阶段 12 会在此基础上再组合：

```text
topic_match_score
publication_recency_score
email_contactability_score
```

并生成临时 `lead_score` 和 `priority`。

## 7. topic_match_reason 说明

每条结果都保留解释文本。

命中时：

```text
Matched keywords: xxx. Target service type: xxx. default rule / pending client keyword hierarchy.
```

无命中时：

```text
No matched keywords. default rule / pending client keyword hierarchy.
```

其中：

```text
default rule / pending client keyword hierarchy
```

表示当前还没有甲方正式关键词层级表，所以使用第一版默认规则。

## 8. 测试覆盖

新增测试覆盖：

```text
title 命中
abstract 命中
MeSH 命中
keywords 命中
service_type 写入
无命中
大小写差异
空摘要 / 空关键词
Lead 字段补齐
批量 Lead 字段补齐
```

测试不访问真实网络。

## 9. 测试命令和结果

阶段 11 相关测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_pubmed_scoring.py
```

结果：

```text
12 passed
```

全量回归测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

结果：

```text
92 passed
```

## 10. 已知限制

```text
1. 当前是基础关键词规则，不是语义匹配
2. 不识别同义词和缩写映射
3. 不使用客户正式关键词层级表
4. 不判断客户真实服务需求强弱
5. 不生成最终 lead_score 和 priority
6. 不替代后续阶段 12 的临时评分
```

## 11. 验收结论

阶段 11 已完成：

```text
每条可评分 Lead 可输出 matched_keywords
可写入 target_service_type
可输出 topic_match_score
可输出 topic_match_reason
结果稳定、可测试
不依赖 LLM
不访问真实网络
未进入阶段 12
全量 pytest 通过
```
