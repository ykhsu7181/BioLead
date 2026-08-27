# PubMed 阶段 20A：统一业务入口 Service 化

日期：2026-08-20

## 1. 阶段目标

阶段 20A 的目标是确认并补齐 PubMed 的统一业务入口，使 CLI、Streamlit 和后续 Agent Tool 都能复用同一个 Service。

本阶段不新增 ToolRegistry，不做 Agent Loop，不接入 LLM，不生成邮件草稿，不发送邮件。

## 2. 当前结论

项目中已经存在统一入口：

```text
src/scholarlead_agent/services/pubmed_service.py
```

核心函数：

```text
run_pubmed_search(params)
```

因此本阶段没有重复创建第二套 Service，而是在现有实现上补齐返回结构和测试。

## 3. 本阶段补齐内容

`PubMedRunResult` 新增面向后续 Tool 复用的稳定字段：

- `search_params`
- `raw_files`
- `processed_files`
- `started_at`
- `finished_at`

原有字段继续保留：

- `task_id`
- `status`
- `pmids`
- `papers`
- `leads`
- `raw_paths`
- `processed_paths`
- `run_report_path`
- `run_report`
- `errors`

## 4. CLI / Streamlit 复用关系

CLI：

```text
pubmed_main.py
→ validate_pubmed_search_inputs(...)
→ run_pubmed_search(...)
→ 打印摘要
```

Streamlit：

```text
streamlit_app.py
→ validate_pubmed_search_inputs(...)
→ run_pubmed_search(...)
→ 展示 Papers / Leads / Run Report / 下载文件
```

后续 Agent Tool 可直接调用：

```text
run_pubmed_search(PubMedSearchParams(...))
```

## 5. 错误行为

Service 继续保留第一轮错误语义：

- 参数错误由校验函数提前拦截；
- ESearch 失败返回 `failed`；
- EFetch 或处理失败返回 `partial_failure`；
- raw 已保存后，后续失败不删除 raw；
- Run Report 继续记录状态、错误、raw 路径和 processed 路径。

## 6. 测试

新增测试文件：

```text
tests/test_pubmed_service.py
```

覆盖内容：

- 正常 mock 端到端 Service；
- 返回结构稳定；
- ESearch 失败；
- EFetch 失败时 raw 保留；
- 参数错误；
- CLI 调用共享 Service；
- Streamlit 引用共享 Service；
- 测试不访问真实网络。

## 7. 验收状态

已完成。

验证结果：

- Service 测试：`6 passed`
- CLI / UI 相关测试：`7 passed`
- 全量 pytest：`123 passed`

## 8. 已知限制

- 本阶段只是 Service 化，不实现 Agent Tool；
- 不处理自然语言输入；
- 不调用 LLM；
- 不生成邮件草稿；
- 不发送真实邮件；
- 不新增数据库。
