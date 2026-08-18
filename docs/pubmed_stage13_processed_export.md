# PubMed 阶段 13：Processed 数据导出

## 1. 本阶段目标

阶段 13 的目标是把已经结构化的 PubMed papers 和 leads 导出为稳定的 JSON / CSV 文件，供后续查看、筛选、演示和阶段 14 Run Report 引用。

本阶段只做 processed 数据导出，不做 Run Report。

## 2. 本阶段输出文件

输出目录：

```text
data/processed/pubmed
```

文件名格式：

```text
pubmed_papers_{safe_query}_{timestamp}.json
pubmed_papers_{safe_query}_{timestamp}.csv
pubmed_leads_{safe_query}_{timestamp}.json
pubmed_leads_{safe_query}_{timestamp}.csv
```

示例：

```text
pubmed_papers_single-cell_RNA_sequencing_cancer_20260817_120000.json
pubmed_leads_single-cell_RNA_sequencing_cancer_20260817_120000.csv
```

## 3. 本阶段不做什么

```text
不访问真实网络
不重新采集 PubMed
不重新解析 XML
不修改 Lead 生成逻辑
不修改 Lead 去重逻辑
不生成 Run Report
不进入阶段 14
不接入 LLM
不发送邮件
```

## 4. 涉及文件

### 4.1 修改文件

```text
src/scholarlead_agent/pubmed_storage.py
```

新增 processed 导出路径和保存函数。

```text
tests/test_pubmed_storage.py
```

扩展 processed JSON / CSV 导出测试。

### 4.2 新增文档

```text
docs/pubmed_stage13_processed_export.md
```

## 5. 新增核心函数

```python
build_pubmed_processed_output_paths(...)
```

生成 papers / leads 的 JSON / CSV 输出路径。

```python
save_pubmed_papers_json(...)
save_pubmed_papers_csv(...)
```

保存结构化 PubMed paper 数据。

```python
save_pubmed_leads_json(...)
save_pubmed_leads_csv(...)
```

保存结构化 PubMed lead 数据。

```python
save_pubmed_processed_outputs(...)
```

一次性保存 papers 和 leads 的 JSON / CSV。

## 6. JSON 导出规则

JSON 使用：

```text
UTF-8
ensure_ascii=False
indent=2
```

这样可以：

```text
1. 保留中文和 Unicode 字符
2. 保留 list / nested 结构
3. 方便人工查看和后续程序读取
```

## 7. CSV 导出规则

CSV 使用：

```text
utf-8-sig
```

也就是带 UTF-8 BOM，方便 Excel 直接打开。

CSV 中：

```text
1. 列名使用清晰英文标题
2. 分数保持数字写入
3. list 字段使用稳定 JSON 字符串序列化
4. 缺失状态保留 missing / unknown / needs_review 等语义
5. 单条数据字段缺失不会导致整批导出失败
```

## 8. Papers CSV 字段

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

## 9. Leads CSV 字段

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

## 10. 测试覆盖

新增测试覆盖：

```text
processed 文件名包含 query + timestamp
papers JSON 可重新读取
papers CSV 可读取
leads JSON 可重新读取
leads CSV 可读取
CSV 存在 UTF-8 BOM
中文 / Unicode 不乱码
分数字段写入
缺失状态保留
多条 papers / leads 导出
```

测试不访问真实网络。

## 11. 测试命令和结果

阶段 13 相关测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_pubmed_storage.py
```

结果：

```text
9 passed
```

全量回归测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

结果：

```text
107 passed
```

## 12. 已知限制

```text
1. 本阶段只负责写文件，不负责端到端 CLI 串联
2. 本阶段不生成 Run Report
3. CSV 中 list 字段采用 JSON 字符串，便于稳定读取，但人工查看时不如分号拼接简洁
4. 导出字段目前围绕第一轮 PubMed 主链路，后续多数据源字段需要再扩展
```

## 13. 验收结论

阶段 13 已完成：

```text
papers JSON 可导出
papers CSV 可导出
leads JSON 可导出
leads CSV 可导出
文件名包含 query 和 timestamp
CSV 使用 Excel 友好的 UTF-8 BOM
Unicode 可正常保存
缺失状态可保留
不访问真实网络
未进入阶段 14
相关测试通过
全量 pytest 通过
```
