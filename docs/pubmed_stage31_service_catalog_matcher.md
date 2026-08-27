# 阶段 31：Company Service Catalog 与 ServiceMatcher

## 目标

本阶段让 ScholarLead Agent 可以根据论文标题、摘要、关键词和研究方向匹配公司已有业务。

第一版使用确定性规则，不让 LLM 自由创造公司不存在的服务。

## 实现内容

新增公司业务配置：

- `data/config/company_services.csv`

新增模块：

- `service_catalog.py`
- `service_matching.py`

新增核心对象：

- `CompanyService`
- `CompanyServiceCatalog`
- `ServiceMatchInput`
- `ServiceMatchResult`

## 匹配规则

第一版规则：

- positive_keywords 命中加分
- synonyms 命中加分
- application_fields 命中加分
- supported_organisms 命中少量加分
- negative_keywords 命中扣分
- enabled=false 的服务不作为可推荐服务

## 输出字段

Service Match 输出：

- service_id
- service_name
- match_score
- match_reason
- matched_terms
- evidence
- status
- catalog_version
- matcher_version

状态包括：

- matched
- no_match
- needs_review
- disabled_service

## 版本追溯

每条匹配结果记录：

- catalog_version
- matcher_version

这样后续公司业务表或匹配规则修改后，历史匹配结果仍可追溯。

## 不做内容

本阶段不做：

- Agent Tool 注册
- 邮件草稿自动补全
- 批量邮件
- 前后端分离
- 新数据源接入
- LLM 语义匹配

## 验收结果

本阶段满足：

- 公司服务从外部 CSV 加载；
- 修改 CSV 不需要修改核心代码；
- 可输出 service_id / score / reason / evidence；
- 没有合适服务时返回 no_match；
- 不允许伪造服务；
- 每条匹配结果保留 catalog_version 和 matcher_version；
- 测试不访问真实网络。

