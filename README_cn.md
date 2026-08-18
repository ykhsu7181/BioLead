# ScholarLead Agent 中文说明

ScholarLead Agent 是一个面向海外科研客户发现的 Python 项目原型。当前重点是 PubMed 第一轮确定性主链路：采集公开论文数据，保留原始证据，提取候选研究人员线索，生成 PubMed 单源临时评分，并导出可人工检查的文件。

当前第一轮不是完整 AI Agent 交付。现在不使用 LLM，不实现 Agent Loop，不使用数据库，不做网页界面，也不发送真实邮件。

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

## 已实现

- 标准 `src` Python 项目结构。
- Python 包：`scholarlead_agent`。
- OpenAlex Works 采集和回归测试。
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

## 本轮未实现

- Crossref。
- NIH RePORTER、NSF 等基金源。
- ORCID 或其他研究人员身份补全。
- 多数据源 Lead 合并。
- 正式四维评分。
- LLM 调用。
- Agent Loop 或 ToolRegistry。
- 个性化邮件草稿生成。
- 真实邮件发送。
- Streamlit 或其他网页界面。
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

## 文档

详细计划和阶段文档位于 `docs/`，包括：

- `pubmed_first_round_implementation_plan_v2.md`
- `pubmed_stage10_lead_dedup.md`
- `pubmed_stage11_keyword_matching.md`
- `pubmed_stage12_temporary_scoring.md`
- `pubmed_stage13_processed_export.md`
- `pubmed_stage14_run_report.md`
- `pubmed_stage15_end_to_end_cli.md`
