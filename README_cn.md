# ScholarLead Agent 中文说明

ScholarLead Agent 是一个面向海外科研客户发现的 Python 项目原型。当前重点是以 PubMed 为主链路，并逐步接入 Agent 架构：采集公开论文数据，保留原始证据，提取候选研究人员线索，生成 PubMed 单源临时评分，用 Crossref 补充 DOI 和出版元数据，生成可人工审核的英文邮件草稿，并导出可检查的文件。

当前仍不是完整生产交付。项目已经有最小 Agent Loop、Streamlit 页面、邮件草稿、AI 使用记录和 Crossref 元数据查询，但还没有数据库、正式多源评分、邮件审批流和真实邮件发送。

## 当前定位

PubMed 第一轮是一条单数据源内部验证链路：

```text
关键词 / 日期 / max_results
-> PubMed ESearch / EFetch
-> raw 原始数据保存
-> 论文解析和去重
-> 从 affiliation 中提取邮箱证据
-> 生成 Lead 并去重
-> 基础机构和国家识别
-> 关键词和 service type 匹配
-> PubMed 单源临时评分
-> papers / leads JSON 和 CSV 导出
-> Run Report
```

这条链路使用确定性 Python 逻辑，并通过 pytest 测试。测试中使用模拟 HTTP 响应，不访问真实网络。

当前 Agent 可调用：

```text
search_pubmed
search_crossref
search_openalex
generate_email_draft
```

其中 `search_crossref` 只用于补充 DOI 和出版元数据，不生成 Lead，不评分，不判断基金活跃度，也不发送邮件。
其中 `search_openalex` 用于补充 OpenAlex Works 元数据和统一论文 Evidence，不生成 Lead，不评分，不判断基金，也不发送邮件。

## 已实现

- 标准 `src` Python 项目结构。
- Python 包：`scholarlead_agent`。
- OpenAlex Works 采集和回归测试。
- Crossref Works 元数据采集和回归测试。
- OpenAlex Service / `search_openalex` Agent Tool。
- PubMed ESearch / EFetch client，包含超时、User-Agent 和重试。
- PubMed raw ESearch JSON、EFetch XML、request meta 保存。
- PubMed XML 解析为结构化 paper。
- PubMed paper 去重：优先 DOI，其次 PMID。
- 只从 PubMed affiliation 文本提取邮箱。
- Lead 生成、Lead 去重、人工审核标记。
- affiliation 中的基础机构和国家识别。
- 关键词匹配和 service type 标记。
- PubMed 单源临时评分和优先级。
- papers / leads JSON 和 CSV 导出。
- Run Report 生成。
- CLI 端到端串联。
- PubMed Service。
- ToolRegistry 和 Agent Loop。
- OpenAI-compatible 模型适配器。
- `search_pubmed`、`search_crossref`、`generate_email_draft` 工具。
- Streamlit 轻量页面。
- 英文邮件草稿生成，但只用于人工审核。
- AI usage / Token 调用记录。

## 本轮未实现

- NIH RePORTER、NSF 等基金源。
- ORCID 或其他研究人员身份补全。
- 多数据源 Lead 合并。
- 正式四维评分。
- 真实邮件发送。
- 数据库存储。
- 生产级客户管理平台。

## 环境

Python 版本：

```text
Python 3.11+
```

当前本地虚拟环境：

```text
literature_env
```

在项目根目录安装：

```powershell
cd "D:\ScholarLead Agent"
.\literature_env\Scripts\python.exe -m pip install -r requirements.txt
.\literature_env\Scripts\python.exe -m pip install -e .
```

## NCBI 配置

如需本地配置，可以复制 `.env.example`：

```powershell
copy .env.example .env
```

占位配置：

```text
NCBI_TOOL=ScholarLeadAgent
NCBI_EMAIL=your.email@example.com
NCBI_API_KEY=
```

不要提交真实邮箱、API Key 或其他凭证。`NCBI_API_KEY` 在第一轮中可以为空。

Crossref 可选配置：

```text
CROSSREF_BASE_URL=https://api.crossref.org
CROSSREF_USER_AGENT=ScholarLeadAgent/0.1 (set CROSSREF_MAILTO for contact)
CROSSREF_MAILTO=
```

## 运行 PubMed 第一轮

在项目根目录运行：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main `
  --query "single-cell RNA sequencing cancer" `
  --from-date 2024-01-01 `
  --to-date 2024-12-31 `
  --max-results 10 `
  --country us `
  --service-type scRNA-seq
```

这个命令会真实访问 PubMed。第一次检查建议把 `--max-results` 设小一些。

输入参数：

- `--query`：PubMed 检索关键词。
- `--from-date`：发表开始日期，格式 `YYYY-MM-DD`。
- `--to-date`：发表结束日期，格式 `YYYY-MM-DD`。
- `--max-results`：最大结果数。
- `--country`：可选，目标国家标签。
- `--service-type`：可选，目标服务类型标签。
- `--raw-dir`：可选，raw 输出目录，默认 `data/raw/pubmed`。
- `--processed-dir`：可选，processed 输出目录，默认 `data/processed/pubmed`。

## 输出文件

raw 原始文件：

```text
data/raw/pubmed/*_esearch.json
data/raw/pubmed/*_efetch.xml
data/raw/pubmed/*_request_meta.json
```

processed 处理后文件：

```text
data/processed/pubmed/pubmed_papers_{query}_{timestamp}.json
data/processed/pubmed/pubmed_papers_{query}_{timestamp}.csv
data/processed/pubmed/pubmed_leads_{query}_{timestamp}.json
data/processed/pubmed/pubmed_leads_{query}_{timestamp}.csv
data/processed/pubmed/pubmed_run_report_{query}_{timestamp}.json
```

`pubmed_papers_*.csv` 是论文结果表。`pubmed_leads_*.csv` 是候选客户线索表。`pubmed_run_report_*.json` 记录输入、数量统计、文件路径、状态和错误。

## 运行轻量 Streamlit 界面

安装依赖后，在项目根目录运行：

```powershell
.\literature_env\Scripts\python.exe -m streamlit run src\scholarlead_agent\ui\streamlit_app.py
```

页面复用 CLI 相同的 PubMed Service。点击运行按钮会真实访问 PubMed，第一次建议把 `max_results` 设为 `3` 或 `5`。

页面也包含 Agent 自然语言区域、Lead 详情邮件草稿区域和 AI 使用情况区域。需要模型的功能必须先配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL`。

## 临时评分说明

当前评分是 PubMed 单源临时评分：

```text
研究方向匹配度：50%
发表时效性：30%
邮箱可联系性：20%
```

这不是项目正式四维评分。基金活跃度和外包倾向字段目前保持未评分：

```text
funding_activity_score = null
funding_activity_reason = Funding source not connected in PubMed-only first round
outsourcing_tendency_score = null
official_scoring_status = pending_multi_source_data
```

## 运行测试

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

测试不允许访问真实网络。PubMed 和 OpenAlex 的 HTTP 行为都应使用 mock。

## 安全和口径

- raw 原始数据必须先保存，再处理。
- 不猜测缺失邮箱。
- 不把候选 PI 当成已经确认的通讯作者。
- 不在代码中硬编码 API Key、密码、SMTP 凭证或 token。
- 不提交 `.env`。
- 不把 PubMed 临时评分说成正式四维评分。
- 不把第一轮说成完整 Agent、T+45 或最终交付。
- 不把 Crossref funder 元数据说成活跃基金。
- 当前系统不发送真实邮件。

## 文档

详细计划和阶段文档位于 `docs/`，包括：

- `pubmed_first_round_implementation_plan_v2.md`
- `pubmed_stage10_lead_dedup.md`
- `pubmed_stage11_keyword_matching.md`
- `pubmed_stage12_temporary_scoring.md`
- `pubmed_stage13_processed_export.md`
- `pubmed_stage14_run_report.md`
- `pubmed_stage15_end_to_end_cli.md`
- `pubmed_stage18_streamlit_ui.md`
- `pubmed_stage21a_crossref.md`
- `pubmed_stage21b_unified_models.md`
- `pubmed_stage21c_openalex_agent.md`
- `pubmed_stage23_email_review_permission.md`
- `pubmed_stage24_database_foundation.md`
- `pubmed_stage25_email_send_loop.md`
- `pubmed_stage26_demo_validation.md`
- `pubmed_stage27_email_provider_decision.md`
- `pubmed_stage28_smtp_test_send.md`
- `pubmed_stage29_lead_detail_evidence.md`
- `pubmed_stage30_conversation_task_context.md`
- `pubmed_stage31_service_catalog_matcher.md`
- `pubmed_stage32_auto_email_draft_sender_profile.md`
- `pubmed_stage33_result_package_v1.md`
- `pubmed_stage34_background_job_foundation.md`

## 阶段 34B：运行 FastAPI 后端

FastAPI 是给后续 Vue 前端使用的后端接口层。它只做接口边界，不替代
PubMed、Agent、邮件、数据库等已有业务模块。

在项目根目录运行：

```powershell
$env:PYTHONPATH="src"
.\literature_env\Scripts\python.exe -m uvicorn scholarlead_agent.api.app:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 阶段 34C：运行 Vue 前端骨架

Vue 前端位于：

```text
frontend/
```

另开一个 PowerShell 窗口运行：

```powershell
cd "D:\ScholarLead Agent\frontend"
npm install
npm run dev
```

默认连接的后端地址是：

```text
http://127.0.0.1:8000
```

当前 Vue 只通过 FastAPI 调用后端，不直接访问 PubMed、OpenAlex、LLM、
SMTP、SQLite，也不保存任何 API Key 或邮箱密码。

新增阶段文档：

- `pubmed_stage34a_api_boundary_design.md`
- `pubmed_stage34c_vue_frontend_skeleton.md`
- `pubmed_stage35_batch_email_drafts.md`
- `pubmed_stage36_batch_review_send.md`
- `pubmed_stage37_result_package_v2.md`
- `pubmed_stage38_data_source_adapter_spec.md`

## 阶段 35 / 36：批量邮件草稿、审核和受控发送

阶段 35 已增加批量邮件草稿生成能力，基于数据库中已有的客户线索生成
待人工审核的邮件草稿。

阶段 36 已增加批量审核和受控发送入口。默认推荐先使用：

```text
permission_check
```

这个模式只检查是否允许发送并记录原因，不会真的调用邮箱服务。

另外还有：

```text
test_recipient
real_recipient
```

这两个模式必须依赖后端 `.env` 中的邮箱配置和权限检查。前端不会保存
邮箱密码或 API Key。

## 阶段 37：Result Package v2

阶段 37 已把最终导出包升级到 v2。现在导出包会包含：

```text
customers.csv
papers.csv
funding.csv
evidence.csv
service_matches.csv
email_drafts.csv
email_reviews.csv
email_send_logs.csv
task_summary.json
README.txt
scholarlead_results.xlsx
```

FastAPI 的接口也可以根据数据库中的 `task_id` 生成结果包：

```text
POST /api/result-packages
```

## 阶段 38：新增数据源 Adapter 规范

阶段 38 没有直接接入新的真实数据源，而是规定以后接入 Europe PMC、
bioRxiv、medRxiv、Semantic Scholar、ORCID、机构官网等来源时必须走统一结构：

```text
Client
Parser
Service
Tool Adapter
Unified Converter
Raw Storage
Processed Export
Mocked Tests
Run Report
Source Metadata
```

核心代码：

```text
src/scholarlead_agent/data_source_adapter.py
src/scholarlead_agent/unified_models.py
```

新增数据源不能绕过 raw 保存、EvidenceRecord、测试，也不能让 LLM 猜邮箱、
基金、身份或机构国家。
