# PubMed 第一轮阶段 3：PubMed API Client

日期：2026-08-17  
项目：ScholarLead Agent  
阶段：Stage 3 - PubMed API Client

## 1. 阶段目标

本阶段实现 PubMed 官方 E-utilities Client。

本阶段只负责：

- 构造 ESearch 请求。
- 构造 EFetch 请求。
- 设置 User-Agent。
- 设置 30 秒 timeout。
- 处理 429 和 5xx 重试。
- 从环境变量读取 NCBI 配置。
- 在测试中使用 mock HTTP response。

本阶段不负责：

- 保存 raw 文件。
- 解析 PubMed XML。
- 生成 Lead。
- 评分。
- 导出 JSON / CSV。
- 接入真实 CLI 全流程。

## 2. 本阶段新增和修改

新增代码：

```text
src/scholarlead_agent/pubmed_client.py
```

新增测试：

```text
tests/test_pubmed_client.py
```

修改配置：

```text
src/scholarlead_agent/config.py
.env.example
```

## 3. Client 能力

新增 `PubMedClient`。

当前方法：

```text
esearch(params)
efetch(pmids)
```

`esearch(params)`：

- 输入：`PubMedSearchParams`
- 调用：PubMed ESearch
- 返回：原始 JSON 字典

`efetch(pmids)`：

- 输入：PMID 列表
- 调用：PubMed EFetch
- 返回：原始 XML 文本

## 4. ESearch 请求

接口：

```text
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
```

请求参数：

| 参数 | 值 |
| --- | --- |
| `db` | `pubmed` |
| `term` | query + publication date 范围 |
| `retmode` | `json` |
| `retmax` | `max_results` |
| `sort` | `pub date` |
| `tool` | `NCBI_TOOL` |
| `email` | `NCBI_EMAIL`，可选 |
| `api_key` | `NCBI_API_KEY`，可选 |

当前日期检索表达式：

```text
({query}) AND ("{from_date}"[Date - Publication] : "{to_date}"[Date - Publication])
```

## 5. EFetch 请求

接口：

```text
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
```

请求参数：

| 参数 | 值 |
| --- | --- |
| `db` | `pubmed` |
| `id` | PMID 列表，逗号分隔 |
| `retmode` | `xml` |
| `rettype` | `abstract` |
| `tool` | `NCBI_TOOL` |
| `email` | `NCBI_EMAIL`，可选 |
| `api_key` | `NCBI_API_KEY`，可选 |

当 PMID 列表为空时，Client 会在发起 HTTP 前报错：

```text
pmids cannot be empty
```

## 6. 配置项

`AppConfig` 新增：

```text
pubmed_esearch_url
pubmed_efetch_url
pubmed_user_agent
ncbi_tool
ncbi_email
ncbi_api_key
```

默认值：

```text
pubmed_esearch_url = https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
pubmed_efetch_url = https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
pubmed_user_agent = ScholarLeadAgent/0.1 (set NCBI_EMAIL for contact)
ncbi_tool = ScholarLeadAgent
ncbi_email = None
ncbi_api_key = None
```

`.env.example` 新增占位项：

```text
PUBMED_USER_AGENT=ScholarLeadAgent/0.1 (your.email@example.com)
NCBI_TOOL=ScholarLeadAgent
NCBI_EMAIL=your.email@example.com
NCBI_API_KEY=
```

注意：`.env.example` 只放占位值，不放真实 API Key。

## 7. HTTP 稳定性规则

当前实现：

- timeout：30 秒。
- retry 次数：3 次。
- 可重试状态码：

```text
429
500
502
503
504
```

不可重试示例：

```text
400
401
403
404
```

达到重试上限后，抛出 HTTP 错误。

## 8. 测试覆盖

新增 `tests/test_pubmed_client.py`，覆盖：

- PubMed 检索 term 构造。
- ESearch 请求参数。
- ESearch User-Agent。
- ESearch 可选 `email` 和 `api_key`。
- 未配置时不发送可选 `email` 和 `api_key`。
- EFetch 请求参数。
- EFetch 返回 XML 文本。
- 空 PMID 列表在 HTTP 前失败。
- 429 和 5xx 会重试。
- 达到重试上限会报错。
- 400 不重试。

所有测试都使用 fake session 和 fake response，不访问真实 PubMed。

## 9. 当前测试结果

测试命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

当前结果：

```text
33 passed
```

## 10. 阶段 3 验收结论

阶段 3 已完成。

已经得到：

- PubMed ESearch Client。
- PubMed EFetch Client。
- PubMed 请求参数构造。
- PubMed User-Agent。
- 30 秒 timeout。
- 429 / 5xx retry。
- NCBI 环境变量配置。
- 完整 mock 测试。

尚未实现：

- raw 数据保存。
- PubMed XML 解析。
- 论文结构化。
- 邮箱提取。
- Lead 生成。
- PubMed 单源临时评分。
- processed 导出。

可以进入阶段 4：

```text
原始数据保存
```

阶段 4 建议重点实现：

- `data/raw/pubmed` raw JSON 保存。
- `data/raw/pubmed` raw XML 保存。
- `request_meta.json` 保存。
- 安全文件名。
- query + timestamp 文件命名。
- 解析失败不删除 raw 文件。
