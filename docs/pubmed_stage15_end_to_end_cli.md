# PubMed 阶段 15：端到端 CLI 串联

## 1. 本阶段目标

阶段 15 的目标是把阶段 1 到阶段 14 的 PubMed 单源能力串成一条可运行的 CLI 主链路。

当前主链路覆盖：

```text
parse args
validate inputs
create run context / timestamp / task_id
PubMed ESearch
save ESearch raw
PubMed EFetch
save EFetch raw
save request meta
parse papers
deduplicate papers
build leads
deduplicate leads
enrich affiliation / country / institution
match keywords / service type
score leads
save papers JSON / CSV
save leads JSON / CSV
save run report
print summary
```

## 2. 本阶段不做什么

```text
不接入 LLM
不接入 Agent Loop
不接入 ToolRegistry
不接入 Crossref
不接入基金源
不实现正式四维评分
不生成邮件
不发送邮件
不实现前端页面
不进入阶段 16
```

## 3. 涉及文件

### 3.1 新增文件

```text
src/scholarlead_agent/services/__init__.py
src/scholarlead_agent/services/pubmed_service.py
```

作用：

```text
提供可复用的 PubMed 业务入口 run_pubmed_search(...)
```

这个入口后续可以被 CLI、轻量 UI、Service 或 Agent Tool 复用。

### 3.2 修改文件

```text
src/scholarlead_agent/pubmed_main.py
```

作用：

```text
CLI 参数解析
参数校验
调用 run_pubmed_search(...)
打印运行摘要
根据运行状态返回 exit code
```

```text
tests/test_pubmed_main.py
```

作用：

```text
使用 fake PubMed client 做 mock 端到端测试
```

### 3.3 新增文档

```text
docs/pubmed_stage15_end_to_end_cli.md
```

## 4. 新增核心函数

```python
run_pubmed_search(params, client=None, timestamp=None, task_id=None, ...)
```

作用：

```text
执行 PubMed 第一轮完整主链路，并返回结构化运行结果
```

```python
extract_pmids_from_esearch_response(raw_response)
```

作用：

```text
从 ESearch 原始 JSON 中提取去重后的 PMID 列表
```

## 5. 新增结构

```python
PubMedRunResult
```

包含：

```text
task_id
status
pmids
papers
leads
raw_paths
processed_paths
run_report_path
run_report
errors
```

## 6. CLI 输出摘要

运行完成后，CLI 会输出：

```text
ScholarLead Agent PubMed first-round run completed
Task ID: ...
Status: ...
PMIDs collected: ...
Papers parsed: ...
Leads generated: ...
Leads with verified email: ...
Leads needing review: ...
Unknown country: ...
Raw files: ...
Papers CSV: ...
Leads CSV: ...
Run report: ...
Scoring mode: PubMed single-source temporary scoring
LLM used: no
Agent enabled: no
```

## 7. 失败处理

### 7.1 ESearch 失败

```text
status = failed
尽量生成 run report
记录 errors
CLI 返回 1
```

### 7.2 EFetch 失败

```text
status = partial_failure
保留已保存的 ESearch raw
保存 request meta
生成 run report
记录 errors
CLI 返回 1
```

### 7.3 解析 / 处理 / 导出失败

```text
status = partial_failure
保留已保存的 raw
尽量生成 run report
记录 errors
CLI 返回 1
```

### 7.4 成功

```text
status = success
保存 raw / processed / run report
CLI 返回 0
```

## 8. 测试策略

阶段 15 测试必须模拟 HTTP，不访问真实网络。

当前使用：

```text
FakePubMedClient
```

模拟：

```text
ESearch 返回 idlist
EFetch 返回 fixture XML
EFetch 抛出异常
```

## 9. 测试覆盖

```text
完整 mock ESearch / EFetch
生成 raw 文件
生成 processed 文件
生成 run report
终端摘要可验证
参数错误时不创建 client
EFetch 失败时 raw 不丢失
EFetch 失败时生成 partial_failure report
测试不访问真实网络
```

## 10. 测试命令和结果

阶段 15 相关测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_pubmed_main.py
```

结果：

```text
3 passed
```

全量回归测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

结果：

```text
112 passed
```

## 11. 当前 CLI 运行命令

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main `
  --query "single-cell RNA sequencing cancer" `
  --from-date 2024-01-01 `
  --to-date 2024-12-31 `
  --max-results 25 `
  --country us `
  --service-type scRNA-seq
```

说明：

```text
真实运行 CLI 会调用 PubMed ESearch / EFetch。
测试中不会访问真实网络，全部通过 fake client 模拟。
```

## 12. 已知限制

```text
1. 当前 CLI 已串联主链路，但 README 更新留到阶段 16
2. 当前没有前端页面
3. 当前没有 Agent Tool / Agent Loop
4. 当前没有邮件生成和发送
5. 当前仍是 PubMed 单源临时评分，不是正式四维评分
6. processing 阶段如果失败，会生成 partial_failure report，但不会尝试修复单条坏数据
```

## 13. 验收结论

阶段 15 已完成：

```text
CLI 可调用 PubMed 第一轮主链路
Service 入口可复用
raw 可保存
papers / leads 可生成
国家 / 机构可补齐
关键词 / service type 可匹配
临时评分可生成
processed JSON / CSV 可导出
run report 可保存
mock 端到端测试通过
不访问真实网络进行测试
不接入 LLM
不进入阶段 16
全量 pytest 通过
```
