# PubMed 阶段 10：Lead 国家与机构基础识别说明

> 文件名沿用 `pubmed_stage10_lead_dedup.md`，但本阶段不重新实现 Lead 去重。  
> 阶段 9 已完成 Lead 去重；阶段 10 只在已有 Lead 结构上补充 affiliation 的机构和国家识别结果。

## 1. 本阶段目标

阶段 10 的目标是从 PubMed 作者 affiliation 中提取基础的机构和国家信息，并保留原始 affiliation，方便后续评分、筛选、导出和人工审核。

本阶段完成后，每条 Lead 可以补齐以下字段：

```text
institution
country
country_confidence
country_source
raw_affiliation
```

## 2. 本阶段不做什么

本阶段不做以下内容：

```text
不重新实现 PubMed Client
不重新实现 PubMed Parser
不修改邮箱提取规则
不修改 Lead 生成主逻辑
不修改 Lead 去重主逻辑
不接入 Crossref
不接入 LLM
不接入 Streamlit
不实现邮件生成或发送
不访问真实网络
不进入阶段 11
```

## 3. 涉及文件

### 3.1 新增文件

```text
src/scholarlead_agent/pubmed_affiliation.py
```

职责：

```text
1. 规范化 affiliation 文本
2. 从 affiliation 中识别国家
3. 从 affiliation 中识别机构
4. 保留 raw_affiliation
5. 为 PubMedLead 补齐机构和国家字段
```

### 3.2 修改文件

```text
src/scholarlead_agent/pubmed_models.py
```

职责：

```text
为 PubMedLead 增加 country_source 和 raw_affiliation 字段
```

新增字段带默认值，因此不会破坏已有 Lead 构造方式。

```text
country_source = "unknown"
raw_affiliation = None
```

### 3.3 测试文件

```text
tests/test_pubmed_leads.py
```

职责：

```text
验证国家识别、机构识别、raw_affiliation 保留、confidence/source 字段，以及不破坏原有 Lead 逻辑
```

## 4. 新增核心函数

```python
normalize_affiliation_text(raw_affiliation)
```

作用：清理多余空格，统一 affiliation 文本格式。

```python
identify_country_from_affiliation(raw_affiliation, email=None)
```

作用：识别国家，优先使用 affiliation 文本；邮箱域名只能作为辅助证据。

```python
identify_institution_from_affiliation(raw_affiliation)
```

作用：从 affiliation 中提取最可能的机构名称。

```python
parse_affiliation(raw_affiliation, email=None)
```

作用：一次性返回机构、国家、置信度、来源和原始 affiliation。

```python
enrich_lead_affiliation(lead)
```

作用：给单条 PubMedLead 补齐机构和国家字段。

```python
enrich_leads_affiliation(leads)
```

作用：批量处理 PubMedLead 列表。

## 5. institution 识别规则

第一版使用确定性规则，不使用 LLM。

处理流程：

```text
1. 读取 raw_affiliation
2. 去掉 affiliation 中的邮箱
3. 按逗号和分号拆分片段
4. 去掉纯国家片段
5. 按关键词优先级选择最可能的机构
6. 如果没有命中关键词，则返回第一个可用片段
7. 如果 affiliation 为空，则 institution = None
```

机构关键词优先级：

```text
university
institute
hospital
college
academy
school
centre
center
laboratory
lab
department
```

示例：

```text
Department of Biology, Example University, Boston, USA
```

识别结果：

```text
institution = Example University
```

## 6. country 识别规则

第一版优先从 affiliation 文本中识别国家。

支持以下国家和常见写法：

```text
United States / USA / U.S.A. / US
United Kingdom / UK / England / Scotland / Wales
China / PR China / People's Republic of China
Japan
Germany
France
Canada
Australia
```

如果 affiliation 文本无法判断国家：

```text
country = unknown
country_confidence = unknown
country_source = unknown
```

不允许为了补齐字段而强行猜测国家。

## 7. 邮箱域名规则

邮箱域名只作为辅助证据，不能作为唯一的高置信度来源。

例如：

```text
alice@cam.ac.uk
```

在 affiliation 没有国家信息时，可以辅助判断为：

```text
country = United Kingdom
country_confidence = medium
country_source = email_domain_auxiliary
```

不会输出：

```text
country_confidence = high
```

## 8. confidence 定义

```text
high
```

国家来自 affiliation 原文中的明确国家写法。

```text
medium
```

国家只来自邮箱域名辅助判断。

```text
unknown
```

没有可靠国家证据。

## 9. source 定义

```text
affiliation_text
```

国家来自 affiliation 原文。

```text
email_domain_auxiliary
```

国家来自邮箱域名辅助判断。

```text
unknown
```

没有可靠来源。

## 10. 与 Lead 去重的关系

阶段 9 已完成 Lead 去重，主要规则是：

```text
1. verified email 相同，认为是强匹配
2. 无邮箱时，同一 PMID + 同一作者名，认为是强匹配
3. 同名 + 同机构，只标记为 candidate，需要人工审核
```

阶段 10 不改变这些去重规则。

阶段 10 的作用是：

```text
1. 把原始 affiliation 保留到 raw_affiliation
2. 把 institution 从完整 affiliation 中提取出来
3. 补齐 country / country_confidence / country_source
4. 让后续筛选、评分、导出时可以直接使用结构化字段
```

需要注意：

```text
institution 变得更结构化后，后续如果要继续使用 same_name_institution 规则，需要明确使用哪个阶段的 institution 字段。
```

当前实现没有主动重写阶段 9 的去重逻辑，避免影响已经通过的测试。

## 11. 测试覆盖

新增测试覆盖：

```text
US 国家识别
UK 国家识别
China 国家识别
Japan 国家识别
无法判断国家时返回 unknown
空 affiliation
raw_affiliation 保留
country_confidence 输出
country_source 输出
邮箱域名只能作为辅助证据
enrich_lead_affiliation 能补齐 Lead 字段
```

测试中不访问真实网络。

## 12. 测试命令

相关测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_pubmed_leads.py
```

全量测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

当前执行结果：

```text
tests/test_pubmed_leads.py: 27 passed
full pytest: 80 passed
```

## 13. 当前已知限制

```text
1. 机构识别是基础规则版，不处理所有复杂地址格式
2. 多机构 affiliation 只选一个最可能机构
3. 非英文 affiliation 支持有限
4. 邮箱域名只能辅助判断国家，不能作为高置信度国家来源
5. 国家列表只覆盖第一版指定范围
6. 不处理城市、省州到国家的复杂映射
```

## 14. 阶段 10 验收结论

阶段 10 已达到当前实施方案要求：

```text
已支持基础国家识别
已支持基础机构识别
已保留 raw_affiliation
已有 country_confidence
已有 country_source
未调用 LLM
未访问真实网络
未修改 PubMed Client / Parser / 邮箱提取 / Lead 去重主逻辑
相关测试通过
全量 pytest 通过
```
