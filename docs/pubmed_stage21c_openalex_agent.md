# 阶段21C：OpenAlex 正式接入 Agent 架构

## 本阶段目标

把项目早期已有的 OpenAlex Works 能力整理为正式 Service / Tool，并接入默认 ToolRegistry。

本阶段不是从零重写 OpenAlex，也不替换已有 CLI 逻辑。

## 已完成内容

1. 复用已有 `openalex_client.py` 和 `works.py`。
2. 新增 `OpenAlexService` 风格入口：`run_openalex_search`。
3. 新增 Agent Tool：`search_openalex`。
4. 默认 ToolRegistry 已注册 `search_openalex`。
5. OpenAlex 输出保存到独立目录：
   - `data/raw/openalex`
   - `data/processed/openalex`
6. 新增 OpenAlex run report。
7. OpenAlex `PaperRecord` 可转换为 `UnifiedPaper`。
8. 保留既有 DOI 标准化、abstract_inverted_index 还原和去重逻辑。

## 新增文件

```text
src/scholarlead_agent/services/openalex_service.py
src/scholarlead_agent/tools/openalex_tool.py
tests/test_openalex_service.py
tests/test_openalex_tool.py
docs/pubmed_stage21c_openalex_agent.md
```

## 修改文件

```text
src/scholarlead_agent/storage.py
src/scholarlead_agent/agent/runtime.py
src/scholarlead_agent/agent/loop.py
tests/test_agent_runtime.py
```

## Tool 输入

`search_openalex` 支持：

```text
query
from_date
to_date
max_results
```

规则继续沿用已有 OpenAlex 校验：

- 日期格式：`YYYY-MM-DD`
- `max_results` 范围：1～20
- query 不能为空

## Tool 输出

返回结构包括：

```text
source
task_id
status
query
from_date
to_date
max_results
work_count
unified_paper_count
works
unified_papers
run_report_path
raw_files
processed_files
errors
```

## 当前不做

本阶段不做：

- Lead 生成；
- 正式评分；
- 邮箱提取；
- 基金判断；
- 数据库；
- UI 大改；
- 真实邮件发送。

## 测试覆盖

新增测试覆盖：

- Service 保存 raw / processed / run report；
- Service 生成 UnifiedPaper；
- Service 失败时保存 report；
- Tool 成功返回结构化结果；
- Tool 参数校验；
- Tool 失败返回；
- 默认 ToolRegistry 注册 `search_openalex`。

## 阶段验收

阶段 21C 已达到 v2.3 最小验收要求：

- `search_openalex` 可返回结构化 works；
- abstract_inverted_index 仍由已有测试覆盖；
- DOI 标准化仍由已有测试覆盖；
- raw / processed 保存已实现；
- ToolRegistry 可注册；
- 测试中不访问真实网络。
