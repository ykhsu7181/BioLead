# ScholarLead Agent 当前实施方案与后续计划（v2.5）

版本：v2.5  
日期：2026-08-24  
项目：ScholarLead Agent  
定位：根据当前代码状态重写 v2.4，作为阶段 25 之后的开发依据。

---

## 1. 文档定位

v2.4 的总体方向是合理的，但它的阶段编号和当前项目状态已经不匹配。

当前项目已经完成了 v2.4 中提到的很多内容，例如：

- Crossref 数据源；
- OpenAlex Agent Tool；
- NIH RePORTER Funding Tool；
- 统一模型草稿；
- Entity / Evidence 基础归并；
- 官方四维评分最小草稿；
- 多数据源 Agent 调度；
- Streamlit 前端升级；
- 邮件草稿审核和权限设计；
- SQLite 数据库基础；
- 受控邮件发送边界。

因此，从本文件开始，后续阶段不再回到 v2.4 的 21A～21H 编号，而是从阶段 26 继续。

---

## 2. 当前真实项目状态

### 2.1 已完成能力

当前项目已经具备以下主链路：

```text
自然语言 / 关键词输入
-> Agent Loop / 手动 PubMed CLI
-> ToolRegistry
-> PubMed / Crossref / OpenAlex / NIH RePORTER
-> raw 数据保存
-> processed JSON / CSV
-> Papers / Leads / Researchers / Organizations / Funding / Evidence
-> 临时评分 / 官方评分草稿
-> 邮件草稿生成
-> 人工审核记录
-> 权限检查
-> 受控发送边界
-> 数据库基础 / 文件导出 / Streamlit 展示
```

当前 Agent 可用工具：

```text
search_pubmed
search_crossref
search_openalex
search_funding
generate_email_draft
```

当前没有注册给 Agent 的真实 `send_email` Tool。

### 2.2 当前数据库基础

当前 SQLite 基础已经包含核心表和邮件发送日志表，主要用于后续产品化：

```text
tasks
papers
researchers
organizations
contacts
funding_records
leads
evidence_records
email_drafts
email_reviews
email_send_logs
ai_usage
tool_calls
run_reports
```

数据库目前是基础落库能力，不等于完整后台系统。

### 2.3 当前邮件状态

当前项目已经支持：

- 生成英文邮件草稿；
- 保存人工审核决策；
- 计算发送权限 blocker；
- 构造发送请求；
- 通过显式注入 provider 执行发送边界；
- 写入发送审计和发送日志。

当前项目尚未支持：

- 配置真实 SMTP / Gmail / Outlook / SendGrid / SES；
- Streamlit 页面真实发送按钮；
- Agent 可调用的 `send_email` Tool；
- 批量无人审核发送；
- 多发件账号和额度管理；
- 退订、黑名单、邮件合规策略。

所以当前对外表述应为：

```text
已完成受控邮件发送边界。
默认不真实发送邮件。
真实邮件 provider 仍需后续接入和审批。
```

---

## 3. 当前不能夸大说明的内容

以下内容不能说已经完整完成：

- 生产级客户管理平台；
- 完整前后端分离系统；
- 完整正式四维评分；
- 全球基金覆盖；
- 真实批量邮件发送；
- 多发件账号额度管理；
- 销售跟进闭环；
- 后台配置系统；
- T+45 正式验收完成。

可以说：

```text
项目已形成 ScholarLead Agent 可展示原型。
当前支持 PubMed 主链路、多数据源补充、客户线索展示、基金查询、邮件草稿、审核权限、数据库基础和受控发送边界。
```

---

## 4. 当前最合理路线

当前不应该继续重复做已经完成的数据源接入，而应该进入两个方向：

```text
路线 A：可展示 Demo 稳定化
路线 B：正式交付能力补齐
```

优先级建议：

```text
阶段 26：可展示 Demo 验证与样例数据准备
阶段 27：真实邮件 provider 接入方案确认
阶段 28：Streamlit 邮件发送演示入口（仅测试邮箱和人工确认）
阶段 29：客户详情页和 Evidence 展示增强
阶段 30：正式评分规则配置化
阶段 31：多源 Researcher / Lead 归并增强
阶段 32：后台与前后端分离方案设计
阶段 33：产品化数据库和任务状态管理
阶段 34：T+45 自测与验收材料整理
```

---

## 5. 阶段 26：可展示 Demo 验证与样例数据准备

### 5.1 目标

准备一套可以稳定演示的最小闭环：

```text
查询
-> PubMed 论文
-> PI / Lead
-> NIH Funding
-> 客户详情
-> 邮件草稿
-> 人工审核
-> 权限检查
-> 发送边界状态
-> 日志 / 导出
```

本阶段重点是演示稳定性，不新增大功能。

### 5.2 建议准备内容

至少准备 3 组 Demo 输入：

```text
single-cell RNA sequencing cancer
CRISPR Cas genome imaging
spatial transcriptomics tumor microenvironment
```

每组保存：

- PubMed 查询参数；
- 输出文件路径；
- papers 样例；
- leads 样例；
- funding 查询样例；
- 邮件草稿样例；
- 权限检查结果；
- 已知限制说明。

### 5.3 验收标准

- Streamlit 能展示完整结果；
- CLI 能跑小范围真实 PubMed；
- Agent 能用自然语言调度工具；
- 数据来源可追溯；
- 邮件不会误发；
- 全量 pytest 通过。

---

## 6. 阶段 27：真实邮件 provider 接入方案确认

### 6.1 目标

在写真实发送代码前，先确定邮件方案。

必须由项目方确认：

- 使用哪个发件服务；
- 发件账号；
- 测试收件邮箱；
- 每日额度；
- 是否允许发送给真实 PI；
- 失败重试策略；
- 是否需要退订声明；
- 日志保留范围。

候选方案：

```text
SMTP
Gmail / Google Workspace
Outlook / Microsoft 365
SendGrid
Amazon SES
```

### 6.2 本阶段不做

- 不直接配置真实密码；
- 不把 API Key 写入代码；
- 不开放 Agent 直接发邮件；
- 不做批量群发。

### 6.3 验收标准

- 邮件 provider 已被书面确认；
- `.env.example` 增加占位配置；
- 安全规则明确；
- 测试策略使用 Fake Provider；
- 真实发送只作为人工 smoke test。

---

## 7. 阶段 28：真实测试邮件发送入口

### 7.1 前置条件

只有阶段 27 确认后才能进入。

本阶段的目标不是继续模拟发送，而是在保留当前安全边界的基础上，接入一个真实邮箱服务，完成单封真实测试邮件发送。

真实邮件发送必须借助外部邮箱系统或邮件服务，项目本身不能脱离邮箱基础设施完成投递。可选服务包括：

```text
网易邮箱 / 网易企业邮箱
Gmail / Google Workspace
Outlook / Microsoft 365
SendGrid
Amazon SES
其他甲方确认的企业邮箱服务
```

第一版建议优先使用 SMTP，因为实现简单、便于验证，也适合先接网易邮箱或企业邮箱。

必须满足：

- 草稿状态为 `approved`；
- 邮箱状态为 verified；
- 人工确认收件人、主题和正文；
- 发件账号启用；
- 未超过额度；
- 真实 EmailProvider 配置存在；
- SMTP 授权码 / API Key 只允许放在本地 `.env` 或部署环境变量中；
- 生成审计记录。

### 7.2 配置要求

新增或完善 `.env.example` 中的占位配置，但不得写入真实密码或授权码。

建议第一版配置：

```text
EMAIL_PROVIDER=smtp
EMAIL_SENDER=your_sender@example.com
EMAIL_TEST_RECIPIENT=your_test_recipient@example.com
EMAIL_SEND_ENABLED=false

SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USERNAME=your_sender@example.com
SMTP_PASSWORD=
SMTP_USE_SSL=true
SMTP_TIMEOUT_SECONDS=30
```

说明：

- `SMTP_PASSWORD` 应填写邮箱客户端授权码或应用密码，不建议使用网页登录密码；
- `EMAIL_SEND_ENABLED=false` 是默认安全值，只有本地明确改为 `true` 才允许真实发送；
- 测试阶段可先限制只能发送到 `EMAIL_TEST_RECIPIENT` 或白名单邮箱；
- `.env` 不得提交到 git。

### 7.3 建议实现

新增或完善：

```text
SmtpEmailProvider
Email provider config loader
Email quota check
Streamlit send confirmation panel
email_send_logs 查询展示
```

调用链：

```text
Streamlit 页面
-> 选择 approved 邮件草稿
-> 展示收件人 / 发件人 / Subject / Body
-> 用户勾选确认
-> 点击发送测试邮件
-> PermissionPolicy 检查
-> SmtpEmailProvider 连接真实邮箱服务
-> 返回 sent / failed / blocked
-> 写入 email_send_logs
-> 页面展示发送状态
```

### 7.4 前端操作要求

Streamlit 中只允许显示人工确认后的发送入口。

页面至少展示：

```text
收件人
PI / Lead 名称
发件账号
Subject
Body
发送范围提示
权限 blocker
确认勾选框
发送测试邮件按钮
发送结果
```

如果任一硬条件不满足，按钮必须不可用，并显示原因。

### 7.5 后端权限要求

发送前必须复用当前 `PermissionPolicy` 和 `email_sending` 边界。

硬拒绝条件至少包括：

```text
draft_status != approved
verified_email 缺失
manual_review_required 未解除
真实发送未启用
provider 配置缺失
收件人不在测试邮箱或白名单内
超过额度
```

这些条件不能被 Prompt 或 Agent 回答绕过。

### 7.6 安全边界

第一版只允许：

```text
单封测试邮件
人工逐封确认
指定测试邮箱或白名单邮箱
本地显式启用 EMAIL_SEND_ENABLED=true 后发送
```

禁止：

```text
无人审核自动发送
批量群发
LLM 直接调用 SMTP
失败后无限重试
把 SMTP 密码 / 授权码写入代码或日志
默认向真实 PI 邮箱发送
把 send_email Tool 暴露给 Agent 后不做 ask 确认
```

### 7.7 测试要求

自动化测试仍然不得依赖真实邮箱服务。

pytest 中必须使用 Fake SMTP / Fake Provider，覆盖：

```text
配置缺失 -> blocked
EMAIL_SEND_ENABLED=false -> blocked
未 approved -> blocked
无 verified email -> blocked
非白名单收件人 -> blocked
Fake SMTP 成功 -> sent
Fake SMTP 失败 -> failed
发送结果写入 email_send_logs
Streamlit 按钮状态逻辑
```

真实邮箱发送只作为人工 smoke test，并且只能在本地明确配置后执行。

### 7.8 人工 smoke test

完成代码后，人工测试流程：

```text
1. 准备真实测试发件邮箱；
2. 开启 SMTP / 生成客户端授权码；
3. 在本地 .env 填写 SMTP 配置；
4. 设置 EMAIL_SEND_ENABLED=true；
5. 设置 EMAIL_TEST_RECIPIENT 为自己的测试收件邮箱；
6. 启动 Streamlit；
7. 选择 approved 草稿；
8. 人工确认后点击发送测试邮件；
9. 检查收件箱是否收到邮件；
10. 检查 email_send_logs 是否记录 sent / failed。
```

### 7.9 验收标准

阶段 28 完成必须满足：

```text
真实 SMTP Provider 可配置
默认不发送，必须显式启用
Streamlit 有人工确认发送入口
只能发送 approved + verified 的单封测试邮件
发送结果可见
发送日志可查
pytest 不访问真实邮箱服务
全量 pytest 通过
```

---

## 8. 阶段 29：客户详情与 Evidence 展示增强

### 8.1 目标

让用户能清楚看到一个 Lead 为什么被推荐。

客户详情应展示：

- PI / 候选人姓名；
- 邮箱和邮箱来源；
- 机构和国家；
- 最近论文；
- 命中关键词；
- 基金记录；
- 评分依据；
- 数据源链接；
- 需要人工确认的原因。

### 8.2 验收标准

- 每个关键字段都有来源或说明；
- 不确定字段明确显示 `unknown` / `needs_review`；
- 不把推断内容写成事实；
- UI 和 Agent 使用同一套结构。

---

## 9. 阶段 30：正式评分规则配置化

### 9.1 目标

把当前官方评分草稿继续完善为可配置、可解释、可对照的评分模块。

默认维度仍为：

```text
资金活跃度：40%
研究方向匹配：30%
发表时效性：20%
外包倾向：10%
```

### 9.2 要求

- 权重集中配置；
- 阈值集中配置；
- 每个维度必须有 evidence；
- 缺少证据时不得硬算总分；
- LLM 可以写解释，但不能当唯一打分器。

---

## 10. 阶段 31：多源 Researcher / Lead 归并增强

### 10.1 目标

减少同一个 PI 在多个数据源中重复出现的问题。

强匹配信号：

- verified email；
- ORCID；
- OpenAlex Author ID；
- 明确个人主页；
- 稳定机构 + 论文关系。

弱匹配信号：

- 姓名；
- 国家；
- 机构文本；
- 研究方向；
- 共同关键词。

### 10.2 禁止

```text
只按姓名直接合并
只按机构直接合并
LLM 猜测同一个人
```

---

## 11. 阶段 32：前后端分离方案设计

当前不急于直接重写成 Vue / FastAPI。

建议在以下条件满足后再做：

- Demo 流程稳定；
- 邮件发送方案确认；
- 数据库结构基本稳定；
- 用户操作路径明确；
- 需要多人使用或长期保存任务。

建议架构：

```text
Vue 前端
-> FastAPI 后端
-> Service 层
-> AgentRunner / ToolRegistry
-> Database / Data Sources / Email Provider
```

Streamlit 可继续作为内部调试入口保留。

---

## 12. 阶段 33：产品化数据库与任务状态管理

### 12.1 目标

从“文件 + 最小 SQLite”升级为更接近产品的数据工作台。

重点补齐：

- 任务状态；
- Tool 调用记录；
- 邮件草稿编辑历史；
- 邮件发送状态；
- 客户跟进状态；
- 配置项管理；
- AI usage 阈值提醒。

### 12.2 原则

- raw 文件继续保留；
- JSON / CSV 导出继续保留；
- 数据库不保存 API Key；
- migrations 必须有测试。

---

## 13. 阶段 34：T+45 自测与验收材料

### 13.1 目标

整理正式验收材料，而不是继续零散加功能。

至少准备：

- 功能完成度矩阵；
- 数据源可行性说明；
- 字段清单；
- 测试报告；
- Demo 输入与输出样例；
- 已知限制；
- 下一阶段计划；
- 安全与合规说明。

### 13.2 验收口径

可以说明：

```text
当前版本已经覆盖 PubMed 主链路、多数据源补充、基金查询、客户详情、邮件草稿、人工审核和受控发送边界。
```

不能说明：

```text
已经完成生产级自动销售系统。
已经可以无人审核批量发送真实邮件。
已经覆盖全球全部基金。
已经通过终验。
```

---

## 14. 后续 Codex 执行规则

每次只执行一个阶段。

每个阶段开始前必须：

1. 阅读本文件；
2. 阅读相关源码；
3. 阅读相关测试；
4. 说明准备修改哪些文件；
5. 不重写已经稳定通过测试的模块。

每个阶段完成后必须汇报：

```text
1. 修改文件
2. 新增函数 / 类 / Tool / Schema
3. 是否修改已有接口
4. 新增状态或错误码
5. 新增测试
6. 局部测试结果
7. 全量 pytest 结果
8. 是否达到本阶段验收标准
9. 已知限制
10. 下一阶段建议，但不自动开始
```

统一安全要求：

- 测试不访问真实网络；
- LLM 测试使用 Fake Model；
- 邮件测试使用 Fake Provider；
- 不提交 `.env`；
- 不记录密钥；
- 不猜测邮箱；
- 不猜测基金；
- 不让 LLM 绕过权限系统；
- 不开放无人审核邮件发送。

---

## 15. 当前下一步建议

最建议下一步执行：

```text
阶段 26：可展示 Demo 验证与样例数据准备
```

原因：

- 当前代码已经有较多能力；
- 继续加新模块之前，需要先验证演示链路是否顺；
- 需要准备可以给师姐或项目方看的稳定样例；
- 邮件真实发送前还需要 provider 和合规口径确认。

一句话总结：

```text
当前项目已经不是“刚接 PubMed”的阶段，而是进入“可展示原型稳定化 + 邮件真实发送方案确认 + 正式交付补齐”的阶段。
```
