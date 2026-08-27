# 阶段 26：可展示 Demo 验证与样例数据准备

日期：2026-08-25  
项目：ScholarLead Agent  
依据文档：`docs/pubmed_first_round_implementation_plan_v2.5.md`

---

## 1. 阶段目标

本阶段只做可展示 Demo 验证和样例整理，不新增大功能。

目标是准备一条可以讲清楚、跑得通、不会误导的演示链路：

```text
关键词 / 自然语言输入
-> PubMed 小范围检索
-> Papers / Leads
-> NIH Funding 样例
-> 客户详情
-> 邮件草稿
-> 人工审核
-> 权限检查
-> 发送边界状态
-> 日志 / 导出
```

注意：当前阶段仍不发送真实邮件。

---

## 2. 当前 Demo 能力状态

当前已经可以展示：

- PubMed 小范围真实检索；
- raw / processed 文件保存；
- papers / leads JSON 和 CSV 导出；
- lead 邮箱证据、机构、国家、评分和人工审核标记；
- NIH RePORTER Funding 查询样例；
- Agent Tool 调用摘要；
- Streamlit 中英切换页面；
- 邮件草稿生成和人工审核；
- 发送权限 blocker；
- 受控发送边界。

当前还不能展示为“已完成”的内容：

- 真实 SMTP / Gmail / Outlook 发信；
- Streamlit 真实发送按钮；
- Agent 直接调用 `send_email`；
- 批量群发；
- 完整正式四维评分；
- 生产级客户管理后台。

---

## 3. Demo 输入准备

### Demo 1：single-cell RNA sequencing cancer

用途：展示 PubMed 检索、论文解析、Lead 生成、邮箱状态、临时评分、NIH Funding 样例。

PubMed 参数：

```text
query = single-cell RNA sequencing cancer
from_date = 2025-01-01
to_date = 2025-12-31
max_results = 5
service_type = scRNA-seq
```

已有输出：

```text
data/raw/pubmed/single-cell_RNA_sequencing_cancer_20260825_094308_988793_esearch.json
data/raw/pubmed/single-cell_RNA_sequencing_cancer_20260825_094308_988793_efetch.xml
data/raw/pubmed/single-cell_RNA_sequencing_cancer_20260825_094308_988793_request_meta.json

data/processed/pubmed/pubmed_papers_single-cell_RNA_sequencing_cancer_20260825_094308_988793.json
data/processed/pubmed/pubmed_papers_single-cell_RNA_sequencing_cancer_20260825_094308_988793.csv
data/processed/pubmed/pubmed_leads_single-cell_RNA_sequencing_cancer_20260825_094308_988793.json
data/processed/pubmed/pubmed_leads_single-cell_RNA_sequencing_cancer_20260825_094308_988793.csv
data/processed/pubmed/pubmed_run_report_single-cell_RNA_sequencing_cancer_20260825_094308_988793.json
```

运行结果摘要：

```text
status = success
pmid_count = 5
paper_count = 5
lead_count = 9
leads_with_verified_email_count = 6
missing_email_count = 3
unknown_country_count = 2
```

NIH Funding 样例：

```text
data/raw/nih_reporter/nih_reporter_single-cell_RNA_sequencing_cancer_20260825_094338_078887_projects.json
data/raw/nih_reporter/nih_reporter_single-cell_RNA_sequencing_cancer_20260825_094338_078887_request_meta.json

data/processed/nih_reporter/nih_reporter_funding_single-cell_RNA_sequencing_cancer_20260825_094338_078887.json
data/processed/nih_reporter/nih_reporter_funding_single-cell_RNA_sequencing_cancer_20260825_094338_078887.csv
data/processed/nih_reporter/nih_reporter_run_report_single-cell_RNA_sequencing_cancer_20260825_094338_078887.json
```

演示重点：

- 有些 Lead 有 verified email，有些是 missing；
- missing 不会被系统猜邮箱；
- NIH Funding 只是 NIH 公开数据源，不代表全球全部基金；
- PubMed 临时评分不是最终正式评分。

---

### Demo 2：Cas-based genome

用途：展示 PubMed affiliation 中能提取公开邮箱时，系统如何生成可联系 Lead。

PubMed 参数：

```text
query = Cas-based genome
from_date = 2026-04-05
to_date = 2026-04-10
max_results = 5
service_type = 未指定
```

已有输出：

```text
data/raw/pubmed/Cas-based_genome_20260819_160135_201863_esearch.json
data/raw/pubmed/Cas-based_genome_20260819_160135_201863_efetch.xml
data/raw/pubmed/Cas-based_genome_20260819_160135_201863_request_meta.json

data/processed/pubmed/pubmed_papers_Cas-based_genome_20260819_160135_201863.json
data/processed/pubmed/pubmed_papers_Cas-based_genome_20260819_160135_201863.csv
data/processed/pubmed/pubmed_leads_Cas-based_genome_20260819_160135_201863.json
data/processed/pubmed/pubmed_leads_Cas-based_genome_20260819_160135_201863.csv
data/processed/pubmed/pubmed_run_report_Cas-based_genome_20260819_160135_201863.json
```

运行结果摘要：

```text
status = success
pmid_count = 1
paper_count = 1
lead_count = 2
leads_with_verified_email_count = 2
missing_email_count = 0
unknown_country_count = 0
```

演示重点：

- PubMed 页面 Affiliation 中的公开邮箱可以被提取；
- 邮箱来源会保留 PubMed URL；
- 多个作者有邮箱时，会生成多条候选 Lead；
- 系统不会只凭姓名猜测通讯作者。

---

### Demo 3：spatial transcriptomics tumor microenvironment

用途：展示 2026-08-25 新跑的小范围 PubMed Demo，适合演示空间转录组方向。

PubMed 参数：

```text
query = spatial transcriptomics tumor microenvironment
from_date = 2025-01-01
to_date = 2025-12-31
max_results = 3
service_type = spatial-transcriptomics
```

本阶段已执行命令：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main `
  --query "spatial transcriptomics tumor microenvironment" `
  --from-date 2025-01-01 `
  --to-date 2025-12-31 `
  --max-results 3 `
  --service-type spatial-transcriptomics
```

新增输出：

```text
data/raw/pubmed/spatial_transcriptomics_tumor_microenvironment_20260825_144611_211245_esearch.json
data/raw/pubmed/spatial_transcriptomics_tumor_microenvironment_20260825_144611_211245_efetch.xml
data/raw/pubmed/spatial_transcriptomics_tumor_microenvironment_20260825_144611_211245_request_meta.json

data/processed/pubmed/pubmed_papers_spatial_transcriptomics_tumor_microenvironment_20260825_144611_211245.json
data/processed/pubmed/pubmed_papers_spatial_transcriptomics_tumor_microenvironment_20260825_144611_211245.csv
data/processed/pubmed/pubmed_leads_spatial_transcriptomics_tumor_microenvironment_20260825_144611_211245.json
data/processed/pubmed/pubmed_leads_spatial_transcriptomics_tumor_microenvironment_20260825_144611_211245.csv
data/processed/pubmed/pubmed_run_report_spatial_transcriptomics_tumor_microenvironment_20260825_144611_211245.json
```

运行结果摘要：

```text
status = success
pmid_count = 3
paper_count = 3
lead_count = 4
leads_with_verified_email_count = 3
missing_email_count = 1
unknown_country_count = 0
```

可展示样例 Lead：

```text
Kangping Yang | yangkangping0913@email.ncu.edu.cn | China | high priority
Liang Yang | ndefy19441@ncu.edu.cn | China | high priority
Neda Nikbakht | neda.nikbakht@emory.edu | United States | high priority
Yanzheng Gao | missing | China | high priority | manual review required
```

演示重点：

- 同一个查询里同时存在 verified email 和 missing email；
- 系统会保留 raw affiliation；
- 有邮箱的 Lead 可以进入邮件草稿和审核流程；
- missing email 的 Lead 不能进入真实发送。

---

## 4. 推荐演示流程

### 4.1 启动 Streamlit

在项目根目录执行：

```powershell
cd "D:\ScholarLead Agent"
.\literature_env\Scripts\python.exe -m streamlit run src\scholarlead_agent\ui\streamlit_app.py
```

页面中建议展示：

1. 左侧语言切换；
2. Agent / 自然语言任务区域；
3. PubMed 检索任务区域；
4. Sources / Steps；
5. Papers；
6. Leads；
7. Researchers；
8. Funding；
9. Scoring；
10. Email Draft；
11. Report；
12. Downloads；
13. AI usage。

### 4.2 手动 PubMed 小范围演示

建议先使用：

```text
query = spatial transcriptomics tumor microenvironment
from_date = 2025-01-01
to_date = 2025-12-31
max_results = 3
service_type = spatial-transcriptomics
```

原因：

- 结果量小；
- 有多个 verified email；
- 有 missing email 对照；
- 适合解释权限和人工审核。

### 4.3 Agent 自然语言演示

如果已经配置模型：

```text
OPENAI_API_KEY
OPENAI_BASE_URL
OPENAI_MODEL
```

可在 PowerShell 中执行：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.agent_main `
  "帮我找 2025 年以来美国做 single-cell RNA sequencing cancer 的 5 篇论文，并给出有公开邮箱的候选 PI。" `
  --max-turns 6
```

说明：

- Agent 会通过 ToolRegistry 调用工具；
- 是否调用 Funding / Crossref / OpenAlex 取决于模型规划；
- 没有模型配置时不要演示这一步，改用手动 PubMed 入口。

### 4.4 邮件草稿和权限演示

建议选择有 verified email 的 Lead，例如：

```text
Neda Nikbakht | neda.nikbakht@emory.edu
```

演示步骤：

1. 打开 Email Draft；
2. 填写服务说明；
3. 生成英文邮件草稿；
4. 人工编辑 subject / body；
5. 保存修改；
6. 做 approve / reject / request_changes；
7. 查看 send permission；
8. 说明当前不会真实发送邮件。

当前阶段预期口径：

```text
系统可以生成草稿、保存审核、显示发送权限。
真实邮箱发送需要阶段 27 确认 provider，阶段 28 再接 SMTP 或其他邮箱服务。
```

---

## 5. 可追溯性检查

Demo 时每条关键数据都应能说明来源：

| 数据 | 来源说明 |
| --- | --- |
| 论文标题 | PubMed EFetch XML / processed papers |
| PMID | PubMed |
| DOI | PubMed / Crossref 补充时需说明 |
| 邮箱 | PubMed affiliation 原文 |
| 机构 | affiliation 基础识别 |
| 国家 | affiliation 国家规则识别 |
| Lead 分数 | PubMed 单源临时评分 |
| Funding | NIH RePORTER 明确返回结果 |
| 邮件草稿 | 模型生成，仅供人工审核 |
| 发送状态 | 当前仅权限边界，不真实发送 |

---

## 6. 演示时必须说明的限制

- PubMed 不是邮箱数据库，邮箱只来自公开 affiliation；
- missing email 不会被猜测；
- PI / 通讯作者当前是候选判断，不是最终人工确认结果；
- NIH RePORTER 只覆盖 NIH 公开项目，不代表全球全部基金；
- 当前官方评分仍是最小草稿，证据不足时不硬算；
- 当前没有真实邮件 provider；
- 当前没有无人审核群发能力；
- 当前不是生产级前后端分离系统。

---

## 7. 阶段 26 验收检查

| 检查项 | 当前结果 |
| --- | --- |
| Streamlit 能展示完整结果 | 已有入口，需人工打开页面确认 |
| CLI 能跑小范围真实 PubMed | 已完成，Demo 3 成功 |
| Agent 能用自然语言调度工具 | 代码已具备，真实演示需要模型配置 |
| 数据来源可追溯 | 已整理 raw / processed / report 路径 |
| 邮件不会误发 | 当前无真实发送按钮，无 Agent `send_email` Tool |
| 全量 pytest 通过 | 已通过，289 passed |

---

## 8. 推荐对外演示口径

可以说：

```text
当前已经形成 ScholarLead Agent 可展示原型。
它可以从 PubMed 检索论文，生成候选 PI / Lead，展示公开邮箱证据、机构、国家、评分和导出文件。
同时可以补充 NIH Funding 样例，生成英文邮件草稿，并进行人工审核和发送权限检查。
```

不能说：

```text
已经可以自动批量发送真实邮件。
已经覆盖全球全部基金。
已经完成正式生产系统。
已经通过 T+45 或终验。
```

---

## 9. 下一阶段建议

下一阶段建议进入：

```text
阶段 27：真实邮件 provider 接入方案确认
```

但在进入阶段 27 前，需要先确认：

- 使用网易邮箱、企业邮箱、Gmail、Outlook、SendGrid 还是 SES；
- 测试发件邮箱；
- 测试收件邮箱；
- 是否限制白名单；
- 每日最大发送量；
- 是否需要邮件退订和合规声明。

本阶段到此停止，不自动开始阶段 27。

