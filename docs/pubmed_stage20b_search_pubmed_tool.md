# PubMed 阶段 20B：search_pubmed Agent Tool

日期：2026-08-20

## 1. 阶段目标

阶段 20B 的目标是把阶段 20A 的 PubMed Service 包装成第一个业务级 Agent Tool：

```text
search_pubmed
```

本阶段只做 Tool 外壳，不实现 ToolRegistry，不实现 Agent Loop，不接入 LLM，不生成邮件草稿，不发送邮件。

## 2. 新增模块

新增最小 Tool 契约：

```text
src/scholarlead_agent/agent/tool_types.py
```

包含：

- `ToolEffect`
- `ToolResult`
- `ToolDefinition`

新增 PubMed Tool：

```text
src/scholarlead_agent/tools/pubmed_tool.py
```

核心对象和函数：

- `SEARCH_PUBMED_TOOL`
- `SEARCH_PUBMED_INPUT_SCHEMA`
- `search_pubmed(arguments, service_runner=run_pubmed_search)`

## 3. Tool 输入

第一版支持：

- `query`
- `from_date`
- `to_date`
- `max_results`
- `country`
- `service_type`

其中 `query / from_date / to_date / max_results` 必填。

`max_results` 仍然遵守 PubMed 第一轮限制：`1～100`。

## 4. Tool 输出

Tool Result 是结构化结果，包含：

- `success`
- `source = pubmed`
- `task_id`
- `status`
- `paper_count`
- `lead_count`
- `papers`
- `leads`
- `run_report_path`
- `raw_files`
- `processed_files`
- `errors`

Papers 保留：

- `pmid`
- `doi`
- `title`
- `journal`
- `publication_date`
- `publication_year`
- `authors`
- `source_url`

Leads 保留：

- `pi_full_name`
- `verified_email`
- `email_status`
- `email_source_url`
- `name_email_match_confidence`
- `institution`
- `country`
- `lead_score`
- `priority`
- `score_explanation`
- `manual_review_required`

Tool 不返回完整 raw XML。

## 5. 错误码

当前支持：

- `invalid_arguments`
- `pubmed_search_failed`
- `pubmed_fetch_failed`
- `pubmed_processing_failed`
- `tool_execution_error`

Tool 错误会返回给调用方，不会静默吞掉。

## 6. 复用关系

`search_pubmed` 只调用：

```text
run_pubmed_search(...)
```

它不重新实现 HTTP、解析、Lead、评分和导出逻辑。

## 7. 测试

新增：

```text
tests/test_pubmed_tool.py
```

覆盖：

- Tool 定义；
- 输入 Schema；
- 正常调用；
- 空 query；
- 非法日期；
- `max_results=0 / 101`；
- Service 成功结果转换；
- Service 错误转换；
- Service 异常转换；
- 输出保留 PubMed 证据；
- 测试不访问真实网络。

## 8. 验收状态

已完成。

验证结果：

- Tool 测试：`8 passed`
- Service + Tool 测试：`14 passed`
- CLI / UI 相关测试：`7 passed`
- 全量 pytest：`131 passed`

## 9. 已知限制

- 暂无 ToolRegistry；
- 暂无 Agent Loop；
- 暂无自然语言解析；
- 暂无 LLM 调用；
- 暂无邮件草稿；
- 暂无真实邮件发送。
