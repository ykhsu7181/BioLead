# AGENT_cn.md

本文档是 ScholarLead Agent 项目的中文开发规范，供 Codex 和其他 AI 编程助手参考。英文版为 `AGENTS.md`。如果文档之间出现冲突，优先级以本文的“事实来源优先级”为准。

## 项目使命

ScholarLead Agent 在后续规划中也可称为 BioLead。它是一个以证据为基础的科研客户发现和邮件触达流程原型，目标是帮助用户从关键词或自然语言需求出发，得到公开科研证据、结构化客户线索、评分依据、业务匹配、可审核邮件草稿、受控发送记录和结果导出。

长期业务流程是：

```text
用户输入
-> Agent / 任务
-> 公开科研数据采集
-> 原始数据保存
-> 清洗和标准化
-> 统一模型和证据记录
-> 研究者 / 机构 / 线索识别
-> 评分
-> 公司业务匹配
-> 个性化邮件草稿
-> 人工审核
-> 受控发送边界
-> 结果包 / 报告 / 导出
```

开发时不要只优化某个孤立模块，而忽略完整业务闭环。

## 当前项目基线

当前实现基线：Stage 38。

当前已经存在：

- PubMed / Crossref / OpenAlex / NIH RePORTER 数据源接入。
- 统一模型和 EvidenceRecord。
- 论文、研究者、机构、联系人、基金和线索结构。
- ToolRegistry 和有限轮次 Agent Loop。
- OpenAI-compatible 模型适配器。
- Conversation / Task Context。
- SQLite 数据基础。
- Company Service Catalog 和 ServiceMatcher。
- SenderProfile。
- 个性化邮件草稿生成。
- 人工审核和受控发送边界。
- SMTP 测试发送。
- 批量邮件草稿、批量审核和受控批量发送。
- 后台任务基础。
- FastAPI 后端。
- Vue 前端。
- Streamlit 原型页面。
- Result Package v2。
- Data Source Adapter 规范。

PubMed 仍然是当前主要线索发现主链路。其他数据源已经有第一版或辅助证据能力，但还不是完整生产级数据产品。

## 事实来源优先级

当不同文档发生冲突时，按以下顺序判断：

1. 当前用户的明确指令。
2. `AGENTS.md` / `AGENT_cn.md`。
3. `docs/current_project_status.md`。
4. `docs/feature_acceptance_matrix.md`。
5. `README.md` / `README_cn.md`。
6. 当前有效的 next-plan 文档。
7. 阶段实施文档。
8. 已废弃或被替代的历史规划文档。

阶段文档只描述当时阶段的实现和决策，不能单独用于判断项目当前状态。Historical / Superseded 文档不得作为当前开发入口。

## 禁止重复实现

不要创建第二套已有子系统。

新增模块前，先检查以下位置是否已有相同或等价实现：

```text
src/scholarlead_agent/
frontend/
docs/
tests/
```

除非用户明确要求替换，否则应在当前架构上扩展。

重点避免重复实现：

- Agent Loop。
- ToolRegistry。
- SQLite / 数据库层。
- 邮件审核和发送流程。
- FastAPI 应用。
- Vue 前端壳。
- ServiceMatcher。
- Result Package。
- Data Source Adapter 模式。

## Python 开发规则

- 支持 Python 3.11 及以上版本。
- 当前本地虚拟环境名称：`literature_env`。
- 使用现有 `src` 项目结构。
- 主包名：`scholarlead_agent`。
- 代码保持清晰、易读、可测试。
- 公共函数添加类型标注。
- 函数保持小而明确。
- 只有逻辑不明显时才添加注释。
- 避免无关重构。

## 安全规则

- 不得在代码中写入密码、API Key、SMTP 凭据、OAuth Token 或数据库密码。
- 密钥从环境变量或本地 `.env` 读取。
- 不提交 `.env`。
- `.env.example` 只能保留占位示例。
- 日志中不得暴露密钥。
- 文档示例中不要暴露真实收件人列表、客户邮箱或模型 Key。

## 数据规则

- 优先使用官方 API，不优先做网页抓取。
- 原始 API 响应必须先保存，再清洗。
- 尽量保留数据来源证据。
- 记录信息来源。
- 不猜测缺失作者邮箱。
- 不编造 ORCID、机构、基金、基金金额、作者角色或研究方向。
- 不把推断信息当成已确认事实。
- 不确定的数据应标记为需要人工审核。

推荐来源字段：

```text
source_name
source_type
source_id
source_url
retrieved_at
```

## 数据源架构规则

Stage 38 以后新增外部科研数据源时，应遵循：

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
EvidenceRecord
```

业务逻辑不应直接依赖某一个第三方 API 的 JSON 结构。

禁止：

- Vue 直接访问外部科研 API。
- FastAPI Route 绕过 Service 直接访问外部科研 API。
- 跳过 raw 保存。
- 证据进入下游流程时跳过 `EvidenceRecord`。
- 直接把 raw 外部字段送进邮件生成。
- 没有模拟测试就注册新的 Agent Tool。
- 用 LLM 猜邮箱、基金、身份、机构或国家。

每个外部 API 集成都应处理超时、重试、限流、分页、空响应、HTTP 错误、异常响应和可处理范围内的字段变化。后续 API 失败不能导致已经保存的数据丢失。

## 邮件规则

系统支持受控邮件流程：草稿生成、人工审核、权限检查和发送记录。系统不支持 Agent 无人值守自动群发。

重要边界：

- 当前没有注册 Agent 可直接调用的 `send_email` 工具。
- Agent 可以生成或准备草稿，但不能自主发送邮件。
- 真实发送必须经过用户/人工明确动作和权限策略检查。
- 批量发送必须保留限额、幂等、状态日志和失败记录。
- 缺失邮箱保持 missing，不推断、不编造。

## 测试规则

- 每个行为变化都要添加或更新测试。
- 外部 API 测试必须模拟 HTTP，不访问真实网络。
- 保持 PubMed、Crossref、OpenAlex、NIH RePORTER、Agent、数据库、邮件、API 和前端相关回归测试。
- 共享行为变更先跑相关测试，再跑全量回归。

当前全量回归命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

## 文档维护规则

每完成一个阶段，必须更新：

- `docs/current_project_status.md`
- `docs/feature_acceptance_matrix.md`

如果用户可见行为变化，还要更新：

- `README.md`
- `README_cn.md`

不要重写 Stage 1 到 Stage 38 的实施文档，除非发现事实错误、文件损坏或明显编码问题。它们是历史实施记录。

Stage 38 之后的当前开发入口是 `docs/ScholarLead_Agent_next_plan_v2.8.md`。
