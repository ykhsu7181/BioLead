# ScholarLead Agent 数据源可行性说明

版本：v0.2  
日期：2026-08-17

## 1. 接入原则

- 优先使用官方 API、开放 API 或甲方提供的合法授权。
- 不使用绕过登录、破解、违反第三方规则的方式采集数据。
- 原始数据必须先保存，再清洗。
- 每条结构化结果必须保留来源标识、来源链接或来源 ID。
- 邮箱不能猜测，只能来自公开可追溯来源。
- 数据源失败时记录失败原因，不删除已有数据。

## 2. 第一阶段推荐数据源

第一阶段建议先做 PubMed 单源主链路。中期再扩展到不少于 4 类核心数据源。

中期推荐组合：

| 数据源 | 类型 | 作用 | 优先级 |
| --- | --- | --- | --- |
| PubMed | 学术文献 | PMID、标题、摘要、作者、机构、部分邮箱 | P0 |
| OpenAlex | 开放文献图谱 | DOI、作者、机构、论文、概念 | P0 |
| Crossref | DOI 元数据 | DOI、出版信息、作者、基金补充 | P0 |
| NIH RePORTER | 科研基金 | NIH 项目、PI、机构、项目周期 | P0 |
| ORCID | 作者身份 | ORCID、姓名变体、作品、机构 | P1 |
| bioRxiv/medRxiv | 预印本 | 最新研究动态和预印本 | P1 |
| NSF Award Search | 科研基金 | NSF 项目和资助信息 | P1 |

## 3. 数据源可行性矩阵

| 数据源 | 可行性 | 可获取字段 | 主要限制 |
| --- | --- | --- | --- |
| PubMed | 高 | PMID、标题、摘要、作者、机构、期刊、日期、部分邮箱 | 邮箱不是稳定字段，通讯作者不总是明确 |
| OpenAlex | 高 | Work ID、DOI、标题、摘要倒排索引、作者、机构、日期 | 生产建议配置 API key，部分字段需二次补全 |
| Crossref | 高 | DOI、标题、作者、期刊、出版日期、基金信息 | 元数据质量取决于出版社 |
| NIH RePORTER | 高 | 项目编号、PI、机构、项目标题、周期、金额 | 主要覆盖美国 NIH/联邦资助 |
| NSF Award Search | 中高 | Award ID、PI、机构、项目标题、金额、日期 | 主要覆盖 NSF |
| ORCID | 中高 | ORCID iD、姓名、其他姓名、机构、作品 | 公开程度取决于用户隐私设置 |
| bioRxiv/medRxiv | 高 | DOI、标题、作者、摘要、日期、分类 | 预印本需标记状态 |
| CORDIS | 中 | 欧洲项目、机构、经费、周期 | 需注册/API key，流程更复杂 |
| Web of Science | 受限 | 高质量论文、引用、作者、机构 | 需甲方授权账号/API |
| Google Scholar | 低 | 论文和引用 | 无稳定官方公开 API，不建议自动化 |
| ResearchGate/X/Twitter | 低 | 研究动态 | 登录、合规和稳定性风险高 |
| 大学/实验室主页 | 中低 | 邮箱、PI、研究方向 | 页面结构不稳定，适合人工辅助 |

## 4. PubMed 第一轮字段

PubMed 单源第一轮采集字段：

- PMID。
- DOI。
- 标题。
- 摘要。
- 期刊。
- 发表日期。
- 作者。
- 作者机构。
- affiliation 中出现的邮箱。
- MeSH 词。
- 关键词。
- PubMed 来源链接。

## 5. 多源统一字段

后续多源统一为以下对象：

- `Paper`：论文。
- `Author`：作者。
- `Institution`：机构。
- `Grant`：基金。
- `Contact`：邮箱。
- `Lead`：客户线索。
- `Evidence`：来源证据。

## 6. 邮箱规则

邮箱处理必须遵守：

- 不猜测邮箱。
- 只提取公开页面或 API 响应中明确出现的邮箱。
- 记录邮箱来源链接。
- 记录邮箱来源类型。
- 记录邮箱与姓名的对应关系。
- 无法确认对应关系时进入人工确认。

邮箱状态：

- `verified_from_source`：公开来源可追溯。
- `missing`：未检出公开邮箱。
- `invalid_format`：格式无效。
- `manual_review_required`：需要人工确认。

## 7. 去重与归并规则

论文去重优先级：

```text
DOI → PMID → PMCID → OpenAlex ID → 标题 + 年份 + 第一作者
```

客户归并优先级：

```text
ORCID / 已验证邮箱 / 明确主页链接 → 可自动合并
姓名 + 机构 + 论文关系 → 生成候选
只有姓名相同 → 不自动合并
```

## 8. 结论

建议执行顺序：

1. PubMed 单源主链路。
2. OpenAlex 增强。
3. Crossref。
4. NIH RePORTER。
5. ORCID 或 bioRxiv/medRxiv。

Google Scholar、ResearchGate、X/Twitter、无授权 Web of Science 不建议作为自动化核心交付数据源。
