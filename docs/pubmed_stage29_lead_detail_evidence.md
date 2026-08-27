# PubMed 第一轮阶段 29：客户详情页和 Evidence 展示增强

## 目标

本阶段只增强客户详情页，让用户能看清楚一个 Lead 为什么被推荐。

重点不是新增采集源，也不是自动发邮件，而是把已有字段整理成可解释的结构：

- PI / 候选人姓名
- 邮箱和邮箱来源
- 机构和国家
- 最近论文
- 命中关键词
- 临时评分依据
- 数据源链接
- 是否需要人工审核，以及原因

## 实现内容

在 Streamlit 客户详情区域新增两类展示：

1. Lead Detail

   用简洁表格展示候选客户的核心信息，例如姓名、邮箱、机构、国家、论文、关键词、PMID、DOI、人工审核原因。

2. Evidence

   用字段级表格展示每个关键字段的来源、置信度和证据说明。

   表格字段包括：

   - Field
   - Value
   - Source
   - Confidence
   - Evidence

## 复用结构

本阶段新增的详情和证据结构由纯 Python helper 生成，不依赖 Streamlit 页面本身。

这样后续 Agent、Service 或其他前端可以复用同一套结构，避免 UI 和 Agent 各自解释一遍字段。

## 不确定字段处理

本阶段继续遵守保守规则：

- 缺失邮箱显示 `missing`
- 无法确定机构显示 `unknown`
- 无法确定国家显示 `unknown`
- 无来源链接时显示 `unknown`
- 候选 PI 不会被直接说成 confirmed corresponding author
- 人工审核原因显示为 `missing_email_candidate`、`unknown_country`、`needs_review` 或 `not_required`

## 本阶段不做

- 不实现阶段 30
- 不修改评分规则
- 不新增数据源
- 不新增 Agent Tool
- 不实现客户批量邮件发送
- 不把推断内容展示成事实

## 验收结果

本阶段达到 v2.5 中阶段 29 的验收要求：

- 每个关键字段都有来源或说明
- 不确定字段明确显示 `unknown` / `missing` / `needs_review`
- 不把推断内容写成确定事实
- UI 使用的详情结构可以被独立测试和复用

