# PubMed Agent Smoke Test 记录

日期：2026-08-20

## 1. 说明

本文件记录阶段 20F 的 Agent 真实任务测试计划和离线验证结果。

当前自动化测试全部使用 Fake Model，不访问真实模型 API，也不访问真实 PubMed。真实 smoke test 需要本地配置：

```text
OPENAI_API_KEY
OPENAI_BASE_URL
OPENAI_MODEL
```

## 2. 启动命令

CLI Agent 入口：

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.agent_main "帮我找 2025 年以来美国做 single-cell cancer 的 5 篇论文，并给出有公开邮箱的候选 PI。"
```

Streamlit 页面中新增：

```text
Agent / 自然语言任务
```

原手动 PubMed 检索表单仍保留。

## 3. 代表性任务集

| 编号 | 输入目标 | 期望行为 | 自动化状态 |
| --- | --- | --- | --- |
| 1 | 正常关键词 + 日期 + 数量 | 调用 `search_pubmed` | Fake Model 已覆盖 |
| 2 | 带 country | 生成结构化 country 参数 | 待真实 smoke |
| 3 | 带 service_type | 生成结构化 service_type 参数 | 待真实 smoke |
| 4 | 明确需要真实论文 | 调用 PubMed Tool | Fake Model 已覆盖 |
| 5 | 普通常识问题 | 不强制调用 PubMed | Fake Model 已覆盖 |
| 6 | 缺日期 / 数量 | 追问，不私自编造 | 待真实 smoke |
| 7 | PubMed 空结果 | 说明无结果，不编造 PMID | 待真实 smoke |
| 8 | Tool 参数非法 | Tool 错误回填，模型解释或修正 | 20D/20C 已覆盖 |
| 9 | PubMed API 失败 | 明确说明失败，不隐藏错误 | 20A/20B 已覆盖 |
| 10 | 用户要求正式基金 / 四维评分 | 明确 PubMed 单源限制 | 待真实 smoke |

## 4. 离线验证结果

已完成：

- 自然语言任务可以通过 Fake Model 触发 `search_pubmed`；
- Tool Result 按 `tool_call_id` 回填；
- 不需要 Tool 的普通问题不会强制调用 PubMed；
- CLI Agent 入口可测试；
- Streamlit Agent 区域已接入；
- 原手动 PubMed 检索功能保留；
- 离线测试不访问真实模型或真实 PubMed。

## 5. 真实 smoke test 记录

当前未执行真实模型 smoke test。

原因：

- 自动化阶段不应依赖真实模型 API；
- 真实运行需要本地私密 `OPENAI_API_KEY`，不能写入仓库；
- 是否进行真实 smoke test 需要用户在本机配置后手动确认。

## 6. 真实 smoke test 检查项

真实测试时需要记录：

- 输入自然语言；
- 模型生成的 Tool Call；
- Tool 参数；
- PubMed Run Report 路径；
- 最终回答；
- 是否保留 PMID / DOI / 来源链接；
- 是否正确标记 `email_status`；
- 是否没有夸大临时评分；
- 是否没有编造邮箱、基金或来源。
