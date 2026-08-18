# PubMed 第一轮阶段 4：原始数据保存

日期：2026-08-17  
项目：ScholarLead Agent  
阶段：Stage 4 - 原始数据保存

## 1. 阶段目标

本阶段实现 PubMed 原始数据保存能力。

本阶段只负责：

- 构建 PubMed raw 输出路径。
- 保存 ESearch 原始 JSON。
- 保存 EFetch 原始 XML。
- 保存 request meta。
- 使用 query + timestamp 生成文件名。
- 使用安全文件名。
- 使用原子写入。
- 确保后续处理失败不会删除已保存 raw 文件。

本阶段不负责：

- 调用 PubMed API。
- 解析 PubMed XML。
- 生成结构化 paper。
- 提取邮箱。
- 生成 Lead。
- 评分。
- 导出 processed JSON / CSV。

## 2. 本阶段新增内容

新增代码：

```text
src/scholarlead_agent/pubmed_storage.py
```

新增测试：

```text
tests/test_pubmed_storage.py
```

## 3. Raw 输出路径

新增 `PubMedRawOutputPaths`：

```text
esearch_json
efetch_xml
request_meta_json
```

新增函数：

```text
build_pubmed_raw_output_paths(query, raw_dir, timestamp)
```

文件命名规则：

```text
{safe_query}_{timestamp}_esearch.json
{safe_query}_{timestamp}_efetch.xml
{safe_query}_{timestamp}_request_meta.json
```

示例：

```text
single-cell_RNA_sequencing_cancer_20260817_120000_esearch.json
single-cell_RNA_sequencing_cancer_20260817_120000_efetch.xml
single-cell_RNA_sequencing_cancer_20260817_120000_request_meta.json
```

## 4. Raw 保存函数

新增函数：

```text
save_pubmed_esearch_response(raw_response, path)
save_pubmed_efetch_xml(raw_xml, path)
save_pubmed_request_meta(meta, path)
```

保存规则：

- JSON 使用 UTF-8。
- JSON 使用 `ensure_ascii=False`。
- XML 按原始文本保存。
- 保存前自动创建父目录。
- 使用临时文件 + replace 的方式原子写入。

## 5. Request Meta

新增函数：

```text
build_pubmed_request_meta(params, paths, collected_at, status, errors)
```

meta 字段：

```text
source
query
from_date
to_date
max_results
country
service_type
collected_at
status
raw_files
errors
```

示例：

```json
{
  "source": "pubmed",
  "query": "single cell RNA sequencing cancer",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31",
  "max_results": 25,
  "country": "US",
  "service_type": "scRNA-seq",
  "collected_at": "2026-08-17T10:00:00",
  "status": "success",
  "raw_files": {
    "esearch_json": "..._esearch.json",
    "efetch_xml": "..._efetch.xml"
  },
  "errors": []
}
```

失败时可以记录：

```json
{
  "status": "failed",
  "errors": ["EFetch HTTP 503"]
}
```

## 6. 数据不丢失原则

本阶段确认：

- raw 文件先保存。
- 后续解析失败不删除 raw 文件。
- 保存 raw 和后续处理是两个独立动作。
- 测试中已模拟“保存 raw 后解析失败”，raw 文件仍然存在。

## 7. 测试覆盖

新增 `tests/test_pubmed_storage.py`，覆盖：

- safe query + timestamp 文件名。
- ESearch JSON 保存和读取。
- EFetch XML 原文保存和读取。
- request meta 保存和读取。
- 失败状态和错误原因记录。
- raw 文件在后续异常后仍然存在。

## 8. 当前测试结果

测试命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

当前结果：

```text
37 passed
```

## 9. 阶段 4 验收结论

阶段 4 已完成。

已经得到：

- PubMed raw 路径构建。
- ESearch 原始 JSON 保存。
- EFetch 原始 XML 保存。
- request meta 保存。
- query + timestamp 文件命名。
- 原子写入。
- raw 文件不因后续异常丢失。
- 完整 mock / 临时目录测试。

尚未实现：

- PubMed XML 解析。
- Paper 数据结构。
- 论文去重。
- 邮箱提取。
- Lead 生成。
- 临时评分。
- processed JSON / CSV 导出。

可以进入阶段 5：

```text
PubMed XML 解析
```

阶段 5 建议重点实现：

- `src/scholarlead_agent/pubmed_parser.py`
- `tests/fixtures/pubmed_efetch_response.xml`
- `tests/test_pubmed_parser.py`
- PMID、DOI、title、abstract、journal、publication_date、authors、affiliations 解析。
