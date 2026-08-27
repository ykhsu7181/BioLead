# ScholarLead Agent 中文说明

ScholarLead Agent 是一个以证据为基础的科研客户发现和邮件触达流程原型。它包含 Python/FastAPI 后端、Vue 前端、Streamlit 原型页面、Agent 编排、多源科研数据接入、受控邮件流程和可审计结果导出。

后续规划文档中也可能使用 BioLead 作为产品方向名称。当前 Python 包名仍然是 `scholarlead_agent`。

当前项目还不是生产级系统。

## 当前定位

当前基线：Stage 38。

```text
用户输入
-> Agent / 任务
-> PubMed / Crossref / OpenAlex / NIH RePORTER
-> 统一模型 + 证据
-> 研究者 / 机构 / 线索
-> 评分
-> 公司业务匹配
-> 个性化邮件草稿
-> 人工审核
-> 受控发送边界
-> 结果包
```

PubMed 仍然是当前主要线索发现主链路。Crossref、OpenAlex 和 NIH RePORTER 已经作为第一版或辅助证据数据源接入。

## 已实现

- 标准 `src` Python 项目结构和 `scholarlead_agent` 包。
- PubMed ESearch / EFetch 采集、解析、raw 保存、processed 导出、运行报告和测试。
- 只从 PubMed affiliation 公开文本提取邮箱。
- 论文和线索去重。
- 基础机构和国家识别。
- 关键词匹配、服务类型标记、PubMed 临时评分和优先级。
- Crossref Works 查询。
- OpenAlex Works 查询。
- NIH RePORTER 基金查询。
- 统一模型和 EvidenceRecord。
- 保守的研究者、机构、联系人和线索结构。
- 最小证据版正式评分草案。
- ToolRegistry 和有限轮次 Agent Loop。
- OpenAI-compatible 模型适配器。
- Conversation / Task Context。
- Company Service Catalog 和 ServiceMatcher。
- SenderProfile。
- AI 邮件草稿生成，用于人工审核。
- 人工审核和权限策略。
- SQLite 数据基础。
- SMTP 测试发送和发送日志。
- 批量邮件草稿。
- 批量审核和受控批量发送。
- 后台任务基础。
- FastAPI API 边界。
- Vue 前端骨架，并已迁移 PubMed 检索、结果展示、结果包生成和下载。
- Streamlit 原型页面。
- Result Package v2。
- Data Source Adapter 规范。
- AI usage 记录。

## 尚未实现

- ORCID 接入。
- NSF / CORDIS 等更多基金源。
- 生产级多源身份归并。
- 完整生产评分。
- 生产部署。
- 生产级邮件服务治理。
- Agent 无人值守自动外联。
- Agent 可直接调用的 `send_email` 工具。
- 完整 CRM / 销售跟进流程。
- 生产级分布式任务队列。
- 所有历史 Streamlit 功能完整迁移到 Vue。

## 邮件边界

系统支持受控邮件流程：草稿生成、人工审核、权限检查和发送记录。

系统不支持 Agent 无人值守自动群发。

当前没有注册 Agent 可直接调用的 `send_email` 工具。Agent 可以生成或准备草稿，但真实发送必须通过明确的人工审核和受控流程触发。

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

## 配置

复制 `.env.example` 到 `.env`：

```powershell
copy .env.example .env
```

不要提交真实密钥。

常用可选配置包括：

```text
NCBI_TOOL=
NCBI_EMAIL=
NCBI_API_KEY=

OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
OPENAI_FALLBACK_MODEL=

EMAIL_PROVIDER=smtp
EMAIL_SEND_ENABLED=false
EMAIL_SENDER=
EMAIL_TEST_RECIPIENT=
EMAIL_ALLOWED_RECIPIENTS=
EMAIL_DAILY_LIMIT=5

SMTP_HOST=
SMTP_PORT=465
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_SSL=true
SMTP_TIMEOUT_SECONDS=30
```

## 运行 PubMed CLI

在项目根目录运行：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main `
  --query "single-cell RNA sequencing cancer" `
  --from-date 2024-01-01 `
  --to-date 2024-12-31 `
  --max-results 5 `
  --country us `
  --service-type scRNA-seq
```

这个命令会访问真实 PubMed。第一次测试建议把 `--max-results` 设为 `3` 或 `5`。

## 运行 Streamlit 原型页面

```powershell
.\literature_env\Scripts\python.exe -m streamlit run src\scholarlead_agent\ui\streamlit_app.py
```

Streamlit 仍然是原型页面，包含 PubMed 检索、Agent 任务、线索详情、邮件草稿、测试发送入口和结果查看。

## 运行 FastAPI 后端

```powershell
.\literature_env\Scripts\python.exe -m uvicorn scholarlead_agent.api.app:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

## 运行 Vue 前端

另开一个 PowerShell：

```powershell
cd "D:\ScholarLead Agent\frontend"
npm install
npm run dev
```

Vue 前端目前包含前端骨架，并已迁移 PubMed 检索、结果展示和结果包生成/下载等基础能力。

## 输出文件

PubMed raw 原始文件：

```text
data/raw/pubmed/*_esearch.json
data/raw/pubmed/*_efetch.xml
data/raw/pubmed/*_request_meta.json
```

PubMed processed 处理后文件：

```text
data/processed/pubmed/pubmed_papers_{query}_{timestamp}.json
data/processed/pubmed/pubmed_papers_{query}_{timestamp}.csv
data/processed/pubmed/pubmed_leads_{query}_{timestamp}.json
data/processed/pubmed/pubmed_leads_{query}_{timestamp}.csv
data/processed/pubmed/pubmed_run_report_{query}_{timestamp}.json
```

结果包会生成在配置的 processed/export 输出区域，也可以通过已支持的 UI/API 流程下载。

## 运行测试

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

外部 API 测试必须模拟 HTTP，不允许访问真实网络。

## 当前文档入口

- 当前状态：`docs/current_project_status.md`
- 功能矩阵：`docs/feature_acceptance_matrix.md`
- 当前下一步计划：`docs/ScholarLead_Agent_next_plan_v2.8.md`
- 历史阶段记录：`docs/pubmed_stage*.md`
