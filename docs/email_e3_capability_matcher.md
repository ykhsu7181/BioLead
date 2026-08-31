# Email-E3：CapabilityMatcher v1

日期：2026-08-28  
状态：Completed  
范围：确定性能力匹配、结果结构和单元测试  
未做：草稿输入改造、paper_only 草稿、Prompt v2、Quality Validator、数据库、API、Vue。

## 实现内容

新增 `src/scholarlead_agent/capability_matching.py`：

```text
CapabilityMatchInput
-> match_sender_capabilities
-> CapabilityMatchResult
```

输出包含：

```text
capability_match_id
lead_id
items[]
  capability_id
  capability_name
  match_score
  match_reason
  matched_terms
  evidence
status
profile_version
matcher_version
```

## 输入与匹配规则

输入可包含：

```text
paper_title
abstract
keywords
matched_keywords
research_direction（可选）
organism（可选）
lead_id（可选）
```

规则：

- 只使用输入的论文 Evidence 和已加载的 Sender Capability Catalog。
- 不调用 LLM，不读取网络，不使用 Lead Score、国家、机构、邮箱或公司 Service Match。
- `capability_match_input_from_lead()` 不会把 `lead.target_service_type` 作为 `research_direction`，避免将内部业务标签误当作论文事实。
- 只匹配 `enabled = true` 的能力。
- 使用 positive keywords、synonyms、research fields、scientific questions、methods 的可解释词项匹配。
- 只保留分数不低于 `0.24` 的可靠候选，按分数降序、能力 ID 升序稳定排序。
- 最多返回 Catalog 配置中的 6 项能力。

## 状态规则

```text
4-6 项 -> matched
1-3 项 -> partial_match
0 项   -> no_match
```

状态仅记录结果，不新增人工审核 Gate。`no_match` 会在 Email-E4 接入 `paper_only` 草稿分流；本阶段不生成邮件。

## 测试

新增 `tests/test_capability_matching.py`，覆盖：

- 最多返回 6 项匹配能力；
- 1-3 项 partial match 不凑数量；
- 无可靠证据时返回 no_match；
- disabled capability 被忽略；
- 同一输入得到稳定、可导出的结果；
- 从 PubMedLead 构建输入时不复用内部服务标签。

测试不调用 LLM、SMTP 或真实网络。

## 当前限制

- v1 是关键词/规则匹配，不理解复杂语义、否定表达或全文上下文。
- `research_direction` 只有在上游能够提供论文 Evidence 或可追溯 metadata 时才应填写。
- `capability_match_id` 当前是由输入、已选能力、Catalog 版本和 Matcher 版本生成的稳定标识；还未保存到数据库。
- 尚未与草稿、批量流程、Result Package、API 或 Vue 连接。

## 下一步

下一阶段为 `Email-E4：EmailDraftInput v2 与草稿自动化分流`：保留旧 Service Match 字段，接入 Capability Match，并让 0 项能力进入 paper_only 草稿输入，而不阻断草稿生成。
