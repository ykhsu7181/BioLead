# PubMed 第一轮阶段 9：Lead 去重与人工审核标记

日期：2026-08-17  
项目：ScholarLead Agent  
阶段：Stage 9 - Lead 去重与人工审核标记

## 1. 阶段目标

本阶段实现 PubMed Lead 的基础去重和人工审核标记。

本阶段只负责：

- 合并强证据重复 Lead。
- 标记弱匹配候选重复 Lead。
- 保留人工审核标记。
- 保留 source links。

本阶段不负责：

- 国家和机构基础识别。
- 关键词匹配。
- 临时评分。
- processed JSON / CSV 导出。
- 客户实体正式归并。
- 跨数据源实体合并。
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

## 3. Lead 新增字段

`PubMedLead` 新增默认字段：

```text
merge_status = not_merged
merge_reason = None
```

字段含义：

| 字段 | 说明 |
| --- | --- |
| `merge_status` | 当前 Lead 的合并或候选状态 |
| `merge_reason` | 合并或候选标记的原因 |

当前支持：

```text
merge_status = confirmed / candidate / not_merged
merge_reason = email_match / same_pmid_author / same_name_institution / None
```

## 4. 新增函数

新增：

```text
deduplicate_pubmed_leads(leads)
get_pubmed_lead_strong_dedup_key(lead)
```

`deduplicate_pubmed_leads`：

- 输入 `list[PubMedLead]`。
- 返回去重和标记后的 `list[PubMedLead]`。
- 不修改原始 raw 数据。
- 不做跨数据源归并。

`get_pubmed_lead_strong_dedup_key`：

- 优先返回邮箱 key。
- 无 verified email 时返回 PMID + 作者名 key。
- 无有效 key 时返回 `None`。

## 5. 强证据合并规则

### 5.1 verified_email 相同

规则：

```text
verified_email 相同
→ 合并
→ merge_status = confirmed
→ merge_reason = email_match
```

说明：

- 邮箱会转小写后比较。
- 保留第一次出现的 Lead 主体。
- 合并 source links。
- 保留人工审核需求。

### 5.2 同一 PMID + 同一作者名

规则：

```text
pmid 相同 + pi_full_name 相同
→ 合并
→ merge_status = confirmed
→ merge_reason = same_pmid_author
```

说明：

- 适用于无邮箱但同一论文中重复生成的作者候选。
- 不用于跨论文同名作者合并。

## 6. 弱匹配只标记不合并

### 6.1 姓名相同 + 机构相同

规则：

```text
pi_full_name 相同 + institution 相同
→ 不合并
→ 标记 candidate
→ manual_review_required = true
→ merge_reason = same_name_institution
```

说明：

- 这类记录可能是同一个人，也可能是同名同机构的不同人。
- 第一轮不做破坏性自动归并。
- 交给人工审核。

### 6.2 只有姓名相同

规则：

```text
只有 pi_full_name 相同
institution 不同
→ 不合并
→ 不标记 candidate
```

说明：

- 科研人员重名很常见。
- 仅凭姓名不能判断同一人。

## 7. Source Links 合并

强证据合并时：

```text
source_links = 去重后的 source links 合集
```

这样可以保留该 Lead 来自哪些 PubMed 论文页面。

## 8. 测试覆盖

新增测试覆盖：

- 强去重 key 优先使用 verified email。
- 没有 verified email 时使用 PMID + 作者名。
- verified email 相同的 Lead 合并。
- 同一 PMID + 同一作者名的无邮箱 Lead 合并。
- 姓名相同 + 机构相同标记 candidate，不合并。
- 只有姓名相同但机构不同，不合并也不标记。
- 合并时保留 source links。

## 9. 当前测试结果

测试命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

当前结果：

```text
71 passed
```

## 10. 阶段 9 验收结论

阶段 9 已完成。

已经得到：

- PubMed Lead 去重函数。
- PubMed Lead 强去重 key。
- verified email 合并。
- 同 PMID + 同作者名合并。
- 姓名 + 机构弱匹配 candidate 标记。
- 仅姓名相同不合并。
- source links 合并。
- 人工审核标记。
- 完整测试覆盖。

尚未实现：

- 国家和机构基础识别。
- 关键词匹配。
- 临时评分。
- processed JSON / CSV 导出。
- 端到端 CLI 串联。

可以进入阶段 10：

```text
国家与机构基础识别
```

阶段 10 建议重点实现：

- 保留 raw affiliation。
- 从 affiliation 中识别常见国家。
- 无法识别时标记 `unknown`。
- 输出 `country`、`country_confidence`、`country_source`。
- 不把推断国家当作确认事实。
