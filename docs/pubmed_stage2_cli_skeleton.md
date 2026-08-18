# PubMed 第一轮阶段 2：参数模型与 CLI 骨架

日期：2026-08-17  
项目：ScholarLead Agent  
阶段：Stage 2 - 参数模型与 CLI 骨架

## 1. 阶段目标

本阶段只建立 PubMed 第一轮命令行入口和参数模型，不访问 PubMed，不保存数据，不解析 XML。

目标是确保后续阶段可以在稳定、可测试的输入参数基础上继续开发。

## 2. 本阶段新增内容

新增代码文件：

```text
src/scholarlead_agent/pubmed_models.py
src/scholarlead_agent/pubmed_main.py
```

新增测试文件：

```text
tests/test_pubmed_models.py
tests/test_pubmed_main.py
```

修改文件：

```text
pyproject.toml
```

## 3. 参数模型

新增 `PubMedSearchParams`，字段包括：

```text
query
from_date
to_date
max_results
country
service_type
raw_dir
processed_dir
```

默认目录：

```text
raw_dir = data/raw/pubmed
processed_dir = data/processed/pubmed
```

## 4. 参数校验

已实现校验规则：

- `query` 去除首尾空格后不能为空。
- `from_date` 必须是 `YYYY-MM-DD`。
- `to_date` 必须是 `YYYY-MM-DD`。
- `from_date` 必须早于或等于 `to_date`。
- `max_results` 必须在 1 到 100 之间。
- `country` 如果提供，会去除首尾空格并转为大写。
- `service_type` 如果提供，会去除首尾空格。

参数校验失败时，CLI 会退出并显示错误信息，不进入后续流程。

## 5. CLI 入口

当前可运行：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main `
  --query "single cell RNA sequencing cancer" `
  --from-date 2024-01-01 `
  --to-date 2024-12-31 `
  --max-results 25 `
  --country us `
  --service-type scRNA-seq
```

当前输出示例：

```text
ScholarLead Agent PubMed stage 2 initialized
Query: single cell RNA sequencing cancer
Date range: 2024-01-01 to 2024-12-31
Max results: 25
Country: US
Service type: scRNA-seq
Raw directory: data\raw\pubmed
Processed directory: data\processed\pubmed
Network requests: disabled in stage 2
```

## 6. 命令入口

`pyproject.toml` 已新增脚本入口：

```text
scholarlead-pubmed = scholarlead_agent.pubmed_main:main
```

如需使用该命令，重新安装 editable 包：

```powershell
.\literature_env\Scripts\python.exe -m pip install -e .
```

也可以直接使用：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main --help
```

## 7. 网络边界

本阶段不引入 `pubmed_client.py`，因此不会发起真实网络请求。

测试中也不访问真实网络。

当前 CLI 明确输出：

```text
Network requests: disabled in stage 2
```

## 8. 测试结果

已新增测试覆盖：

- 参数标准化。
- 日期格式校验。
- 日期范围校验。
- `max_results` 边界校验。
- 默认 raw / processed 目录。
- CLI 成功输出。
- CLI 可选参数默认值。
- 参数错误时退出。
- 参数错误时不进入后续网络阶段。

测试命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

当前结果：

```text
25 passed
```

## 9. 阶段 2 验收结论

阶段 2 已完成。

已经得到：

- PubMed 参数模型。
- PubMed 参数校验。
- PubMed CLI 骨架。
- PubMed 独立命令入口。
- 阶段 2 测试。

尚未实现：

- PubMed ESearch。
- PubMed EFetch。
- HTTP timeout。
- HTTP retry。
- raw 数据保存。
- XML 解析。
- Lead 生成。

可以进入阶段 3：

```text
PubMed API Client
```

阶段 3 建议新增：

- `src/scholarlead_agent/pubmed_client.py`
- `tests/test_pubmed_client.py`
