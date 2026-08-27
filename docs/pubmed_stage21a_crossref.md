# 阶段21A：Crossref 数据源接入

## 本阶段目标

在 PubMed Agent 化基础上，新增 Crossref 数据源能力，用于补充 DOI 和出版元数据。

本阶段只接入 Crossref，不生成 Lead，不做正式评分，不发送邮件，不引入数据库。

## 已完成内容

1. 新增 Crossref 输入参数和数据模型。
2. 新增 Crossref Works API Client。
3. 新增 Crossref Parser / Normalizer。
4. 新增 Crossref raw / processed / run report 保存。
5. 新增 Crossref Service。
6. 新增 Agent Tool：`search_crossref`。
7. 默认 ToolRegistry 已注册 `search_crossref`。
8. Agent Prompt 已说明 Crossref 只用于 DOI / 出版元数据补充。
9. 新增 Crossref pytest 测试，全部使用 Fake HTTP，不访问真实网络。

## 新增文件

```text
src/scholarlead_agent/crossref_models.py
src/scholarlead_agent/crossref_client.py
src/scholarlead_agent/crossref_parser.py
src/scholarlead_agent/crossref_storage.py
src/scholarlead_agent/services/crossref_service.py
src/scholarlead_agent/tools/crossref_tool.py
tests/test_crossref_models.py
tests/test_crossref_client.py
tests/test_crossref_parser.py
tests/test_crossref_service.py
tests/test_crossref_tool.py
docs/pubmed_stage21a_crossref.md
```

## 修改文件

```text
.env.example
src/scholarlead_agent/config.py
src/scholarlead_agent/agent/loop.py
src/scholarlead_agent/agent/runtime.py
tests/test_agent_runtime.py
tests/test_llm_adapter.py
```

## Crossref 输入参数

第一版支持：

```text
doi
title
max_results
```

规则：

- DOI 优先；
- DOI 为空时使用 title；
- `doi` 和 `title` 至少一个不能为空；
- `max_results` 范围：1～20；
- DOI 会去掉 `https://doi.org/` 或 `http://doi.org/` 前缀，并转成小写。

## HTTP 行为

Crossref Client 使用：

```text
/works/{doi}
/works?query.title=...&rows=...
```

要求：

- timeout 30 秒；
- 429 和 5xx 按配置重试；
- 设置 User-Agent；
- 支持 `mailto` 参数；
- 4xx 直接返回错误；
- JSON 异常会抛出并由 Service 记录。

## 输出目录

Raw：

```text
data/raw/crossref/
```

Processed：

```text
data/processed/crossref/
```

输出文件：

```text
crossref_{query_or_doi}_{timestamp}_works.json
crossref_{query_or_doi}_{timestamp}_request_meta.json
crossref_works_{query_or_doi}_{timestamp}.json
crossref_works_{query_or_doi}_{timestamp}.csv
crossref_run_report_{query_or_doi}_{timestamp}.json
```

## CrossrefWork 字段

```text
source
crossref_id
doi
title
abstract
journal
publisher
publication_date
publication_year
authors
funder_names
reference_count
is_referenced_by_count
source_url
raw_record_path
```

注意：

- `abstract` 可能为空；
- `funder_names` 只来自 Crossref 明确返回的 funder 字段；
- 不把 funder 信息说成“活跃基金”；
- 不把 Crossref 作者直接合并为 PubMed Lead。

## Tool 行为

新增工具：

```text
search_crossref
```

返回：

```text
source
task_id
status
doi
title
max_results
work_count
works
raw_files
processed_files
run_report_path
errors
```

明确不做：

- Lead 生成；
- Lead 评分；
- 邮件发送；
- 基金活跃度判断。

## 测试覆盖

新增测试覆盖：

- DOI 标准化；
- DOI / title 输入校验；
- max_results 限制；
- DOI endpoint；
- title query；
- User-Agent / mailto；
- 429 / 5xx 重试；
- 4xx 错误；
- timeout；
- malformed JSON；
- Crossref response 解析；
- DOI 去重；
- weak key 去重；
- raw / processed / run report 保存；
- Tool 成功和失败返回；
- 默认 ToolRegistry 注册 `search_crossref`。

## 已知限制

1. 当前 Crossref 只补充出版元数据。
2. 当前不生成客户 Lead。
3. 当前不做跨数据源实体合并。
4. 当前不把 Crossref funder 推断为正式基金活跃度。
5. 当前没有 Streamlit 独立 Crossref 表单。
6. 当前没有数据库。

## 验收结果

阶段 21A 已达到当前实施方案的最小验收要求：

- Crossref DOI 查询能力已实现；
- Crossref title 查询能力已实现；
- raw / processed / run report 保存已实现；
- `search_crossref` Tool 已实现并注册；
- Agent Loop 未写死 Crossref；
- 不生成 Lead；
- 不评分；
- 不发邮件；
- 测试中不访问真实网络。
