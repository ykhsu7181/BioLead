# 阶段 30：最小 Conversation / Task Context

## 目标

本阶段为 ScholarLead Agent 增加最小多轮上下文能力，让系统能记住同一个会话中的上一轮任务结果。

第一版只保存必要索引，不做完整长期记忆：

- conversation_id
- task_id
- last_run_report_path
- last_lead_ids
- last_selected_lead_ids
- recent_messages

## 实现内容

新增轻量会话模型：

- ConversationMessage
- TaskContext

新增上下文构造能力：

- 将 TaskContext 压缩为简短 system context
- 只加载最近若干条 user / assistant 消息
- 从 Agent tool result 中提取 task_id、run_report_path、lead_id

新增 SQLite 表：

- conversations
- conversation_messages
- conversation_state

新增 Agent 会话入口：

- run_agent_conversation

该入口会：

1. 创建或读取 conversation_id；
2. 读取上一轮 TaskContext 和最近消息；
3. 运行现有 AgentRunner；
4. 保存 user / assistant 消息；
5. 更新 conversation_state。

## 不做内容

本阶段没有实现：

- Company Service Catalog
- ServiceMatcher
- 批量邮件
- FastAPI
- Vue
- 新数据源
- 完整长期记忆

## 验收

本阶段满足：

- 同一个 conversation_id 可以复用上一轮 task context；
- 新 conversation 不串历史；
- 基础状态可从 SQLite 恢复；
- 单轮 Agent 行为保持兼容；
- 测试不访问真实模型或真实网络。

