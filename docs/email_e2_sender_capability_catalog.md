# Email-E2：Sender Capability Catalog 接入

日期：2026-08-28  
状态：Completed  
范围：本地能力目录、加载、校验、版本读取和测试  
未做：CapabilityMatcher、草稿 Prompt v2、Quality Validator、数据库迁移、API、Vue 改造。

## 实现内容

- 新增 `data/config/sender_capabilities.json`，包含 39 项公司确认的发件方科研能力。
- 将 `selection_policy` 改为机器可读配置：

```json
{
  "target_candidate_count": 4,
  "max_candidate_count": 6,
  "min_candidate_count": 0,
  "allow_fewer_when_evidence_is_insufficient": true,
  "zero_match_strategy": "paper_only",
  "llm_may_create_new_capabilities": false
}
```

- 新增 `src/scholarlead_agent/sender_capabilities.py`。
- 新增 `SenderCapabilitySelectionPolicy`、`SenderCapability`、`SenderCapabilityCatalog` 数据结构。
- 新增 `load_sender_capability_catalog()`、`sender_capability_catalog_to_dict()` 和 `enabled_capabilities`。

## 校验规则

- JSON 顶层、`selection_policy`、`source_policy` 和 `capabilities` 必须是正确结构。
- 能力目录必须非空，能力 ID 不能重复。
- 每项能力必须有 ID、名称、分类、描述、关键词、同义词、研究方向、科学问题、方法和布尔 `enabled`。
- 候选数量必须满足 `min <= target <= max`。
- `zero_match_strategy` 当前只允许 `paper_only`。
- `llm_may_create_new_capabilities` 必须为 `false`。
- disabled capability 会被加载和保留版本信息，但不会出现在 `enabled_capabilities` 中。

## 测试

新增 `tests/test_sender_capabilities.py`，覆盖：

- 正常加载与版本读取；
- 导出结构；
- 缺少必填字段；
- 重复能力 ID；
- 无效候选数量策略；
- disabled capability；
- 项目内 39 项正式能力目录加载。

测试只读取本地 JSON，不调用模型、SMTP 或真实网络。

## 下一步

下一阶段为 `Email-E3：CapabilityMatcher v1`：根据论文标题、摘要、关键词等结构化 Evidence，从本目录中确定性选出 0-6 项能力。该阶段不会让 LLM 决定匹配结果。
