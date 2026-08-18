# PubMed 阶段 14：Run Report

## 1. 本阶段目标

阶段 14 的目标是为每次 PubMed 第一轮运行生成可审计的任务报告，记录输入参数、raw 文件、processed 文件、统计结果、错误信息和当前运行状态。

本阶段只实现 Run Report 的构建与保存能力，不做阶段 15 的端到端 CLI 串联。

## 2. 本阶段不做什么

```text
不访问真实网络
不重新采集 PubMed
不重新解析 XML
不重新导出 processed 文件
不改 PubMed Client / Parser / Lead / Dedup 逻辑
不接入 LLM
不接入 Agent Loop
不发送邮件
不进入阶段 15
```

## 3. 涉及文件

### 3.1 修改文件

```text
src/scholarlead_agent/pubmed_storage.py
```

新增 Run Report 路径、报告构建和保存函数。

```text
tests/test_pubmed_storage.py
```

新增 success / partial failure / failed 三类报告测试。

### 3.2 新增文档

```text
docs/pubmed_stage14_run_report.md
```

## 4. 新增核心函数

```python
build_pubmed_run_report_path(...)
```

生成 Run Report JSON 输出路径。

```python
build_pubmed_run_report(...)
```

根据输入参数、PMID、papers、leads、raw 文件、processed 文件、errors 和运行状态生成报告 dict。

```python
save_pubmed_run_report(...)
```

将 Run Report 保存为 JSON。

## 5. Run Report 文件名

文件名格式：

```text
pubmed_run_report_{safe_query}_{timestamp}.json
```

示例：

```text
pubmed_run_report_single-cell_RNA_sequencing_cancer_20260817_120000.json
```

## 6. 报告核心字段

```text
task_id
source
query
from_date
to_date
max_results
country
service_type
pmid_count
paper_count
lead_count
leads_with_verified_email_count
leads_needing_review_count
missing_email_count
unknown_country_count
raw_files
processed_files
errors
started_at
finished_at
status
scoring_mode
queried_sources
funding_source_status
agent_status
llm_status
```

固定状态说明：

```text
scoring_mode = pubmed_single_source_temporary
queried_sources = ["pubmed"]
funding_source_status = not_connected
agent_status = not_enabled_in_first_round
llm_status = not_used_in_first_round
```

## 7. 统计规则

```text
pmid_count：去重后的 PMID 数量
paper_count：结构化 paper 数量
lead_count：Lead 数量
leads_with_verified_email_count：有 verified_from_pubmed_affiliation 邮箱的 Lead 数量
leads_needing_review_count：manual_review_required = True 的 Lead 数量
missing_email_count：邮箱缺失或 verified_email 为空的 Lead 数量
unknown_country_count：country = unknown 的 Lead 数量
```

## 8. 错误记录规则

`errors` 必须是结构化列表。

每条错误至少包含：

```text
stage
type
message
```

示例：

```json
{
  "stage": "efetch",
  "type": "http_error",
  "message": "EFetch HTTP 503"
}
```

如果上游只提供字符串错误，会被转为：

```json
{
  "stage": "unknown",
  "type": "unknown",
  "message": "error message"
}
```

## 9. 失败状态覆盖

阶段 14 测试覆盖三类状态：

```text
success
partial_failure
failed
```

其中 partial failure 用于类似：

```text
ESearch raw 已保存，但 EFetch 或后续处理失败
EFetch raw 已保存，但 parser 失败
processed 导出部分失败，但 raw 不删除
```

## 10. 测试覆盖

新增测试覆盖：

```text
Run Report 文件名包含 query + timestamp
success 报告统计正确
partial_failure 记录错误且保留 raw 文件
failed 报告记录结构化错误
字符串错误可转为结构化错误
Run Report JSON 可重新读取
scoring_mode 正确
agent / llm / funding 状态正确
```

测试不访问真实网络。

## 11. 测试命令和结果

阶段 14 相关测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_pubmed_storage.py
```

结果：

```text
14 passed
```

全量回归测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

结果：

```text
112 passed
```

## 12. 已知限制

```text
1. 本阶段只提供 Run Report 构建和保存函数
2. CLI 端到端串联留到阶段 15
3. Report 中的 processed_files 依赖调用方传入已经生成的文件路径
4. Report 不负责重新生成 raw 或 processed 文件
```

## 13. 验收结论

阶段 14 已完成：

```text
Run Report 可生成
Run Report 可保存为 JSON
输入参数可追踪
raw / processed 文件路径可记录
核心统计字段可记录
success / partial_failure / failed 可区分
errors 可结构化记录
不访问真实网络
不接入 LLM
未进入阶段 15
相关测试通过
全量 pytest 通过
```
