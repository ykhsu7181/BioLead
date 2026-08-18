# PubMed 阶段 12：单源临时评分

## 1. 本阶段目标

阶段 12 的目标是为 PubMed 第一轮 Demo 生成稳定、可解释、可测试的临时 Lead 分数和优先级。

本阶段评分只基于 PubMed 单源数据，不是合同中的正式四维评分。

## 2. 本阶段补齐字段

```text
topic_match_score
publication_recency_score
email_contactability_score
lead_score
priority
score_explanation
funding_activity_score
funding_activity_reason
outsourcing_tendency_score
official_scoring_status
```

## 3. 本阶段不做什么

```text
不接入基金数据源
不计算正式 funding activity 分数
不计算正式 outsourcing tendency 分数
不做正式四维评分
不接入 LLM
不接入 Agent Loop
不生成邮件
不发送邮件
不访问真实网络
不进入阶段 13
```

## 4. 涉及文件

### 4.1 修改文件

```text
src/scholarlead_agent/pubmed_models.py
```

给 `PubMedLead` 增加阶段 12 字段，全部带默认值，避免破坏已有 Lead 构造逻辑。

```text
publication_recency_score = 0
email_contactability_score = 0
lead_score = 0
priority = "unscored"
score_explanation = "Not scored."
funding_activity_score = None
funding_activity_reason = "Funding source not connected in PubMed-only first round"
outsourcing_tendency_score = None
official_scoring_status = "pending_multi_source_data"
```

```text
src/scholarlead_agent/pubmed_scoring.py
```

在阶段 11 关键词匹配基础上增加 PubMed 单源临时评分函数。

### 4.2 测试文件

```text
tests/test_pubmed_scoring.py
```

扩展阶段 12 评分测试。

## 5. 新增核心函数

```python
score_publication_recency(publication_year, reference_year=None)
```

根据发表年份计算时效性分数。

```python
score_email_contactability(email_status, verified_email)
```

根据 PubMed affiliation 中的邮箱证据计算可联系性分数。

```python
calculate_pubmed_lead_score(...)
```

按照固定权重计算 PubMed 单源临时总分。

```python
assign_priority(lead_score)
```

根据临时总分输出优先级。

```python
build_score_explanation(...)
```

生成可解释评分说明。

```python
build_pubmed_temporary_score(lead, reference_year=None)
```

生成结构化临时评分结果。

```python
score_pubmed_lead(lead, reference_year=None)
```

给单条 Lead 写入阶段 12 评分字段。

```python
score_pubmed_leads(leads, reference_year=None)
```

批量给 Lead 写入阶段 12 评分字段。

## 6. 固定权重

第一轮 PubMed 单源临时评分使用固定权重：

```text
研究方向匹配度 topic_match_score：50%
发表时效性 publication_recency_score：30%
邮箱可联系性 email_contactability_score：20%
```

计算公式：

```text
lead_score =
  topic_match_score * 0.5
  + publication_recency_score * 0.3
  + email_contactability_score * 0.2
```

结果四舍五入为整数。

## 7. publication_recency_score 规则

```text
发表年份缺失：0
未来年份或 0-2 年内：100
3-5 年：70
6-10 年：40
10 年以上：0
```

测试中使用 `reference_year` 固定参考年份，保证结果稳定。

## 8. email_contactability_score 规则

```text
verified_from_pubmed_affiliation 且有邮箱：100
needs_review 且有邮箱：60
缺失邮箱：0
其他状态：0
```

注意：邮箱只影响可联系性分数，不会影响研究方向匹配分。

## 9. priority 规则

```text
lead_score >= 80：high
50 <= lead_score < 80：medium
lead_score < 50：low
```

## 10. 正式评分占位字段

由于当前仍是 PubMed 单源第一轮，没有接入基金源、外包倾向等多源数据，因此必须保留以下占位：

```text
funding_activity_score = None
funding_activity_reason = Funding source not connected in PubMed-only first round
outsourcing_tendency_score = None
official_scoring_status = pending_multi_source_data
```

这表示正式多源评分尚未完成。

## 11. 测试覆盖

新增测试覆盖：

```text
高匹配 + 近期发表 + verified email -> 高分
弱匹配 + 较旧发表 + missing email -> 低分
80 分边界
50 分边界
固定权重计算
priority 分级
score_explanation 有内容
funding / outsourcing 占位字段正确
批量 Lead 评分
```

测试不访问真实网络。

## 12. 测试命令和结果

阶段 12 相关测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_pubmed_scoring.py
```

结果：

```text
22 passed
```

全量回归测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

结果：

```text
102 passed
```

## 13. 已知限制

```text
1. 当前只是 PubMed 单源临时评分
2. 没有接入基金数据源
3. 没有接入 Crossref / ORCID / NIH RePORTER / NSF
4. 没有正式四维评分
5. topic_match_score 仍依赖阶段 11 的基础关键词规则
6. publication_recency_score 只是基础年份规则
7. email_contactability_score 只基于 PubMed affiliation 中的邮箱证据
```

## 14. 验收结论

阶段 12 已完成：

```text
PubMed 单源临时评分已实现
固定权重 50% / 30% / 20% 已实现
priority 分级已实现
score_explanation 已实现
funding / outsourcing 保持未评分占位
official_scoring_status = pending_multi_source_data
不依赖 LLM
不访问真实网络
未进入阶段 13
相关测试通过
全量 pytest 通过
```
