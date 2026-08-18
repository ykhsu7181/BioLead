# PubMed 第一轮阶段 1：项目准备与边界确认

日期：2026-08-17  
项目：ScholarLead Agent  
阶段：Stage 1 - 项目准备与边界确认

## 1. 阶段目标

本阶段不实现 PubMed 业务代码，只确认第一轮开发边界、项目结构、输出目录和测试原则。

阶段 1 的目标是确保后续开发不会一开始就扩散到 LLM、邮件、数据库、网页或多数据源，先把 PubMed 单源主链路做稳。

## 2. 当前项目确认

| 项目 | 当前状态 | 结论 |
| --- | --- | --- |
| 项目名称 | ScholarLead Agent | 确认 |
| Python 包名 | `scholarlead_agent` | 确认 |
| 项目结构 | `src` layout | 确认 |
| Python 版本要求 | Python 3.11+ | 确认 |
| 当前虚拟环境 | `literature_env` | 确认 |
| 当前已实现主模块 | OpenAlex 论文采集 | 保持不破坏 |
| 当前测试框架 | pytest | 确认 |

## 3. 第一轮开发边界

第一轮只做：

```text
PubMed 检索
→ 原始数据保存
→ PubMed XML 解析
→ 论文结构化
→ affiliation 邮箱提取
→ PI / 通讯作者候选 Lead
→ PubMed 单源临时评分
→ JSON / CSV 导出
→ run report
```

第一轮明确不做：

- Crossref。
- OpenAlex 增强。
- NIH RePORTER / NSF 基金采集。
- ORCID。
- bioRxiv / medRxiv。
- LLM。
- Streamlit 或其他网页页面。
- 数据库。
- 邮件草稿真实生成。
- 真实邮件发送。
- 批量邮件发送。
- 自动猜测邮箱。
- 复杂客户归并。
- 正式四维评分。

## 4. 输出目录确认

已为 PubMed 第一轮准备目录占位：

```text
data/raw/pubmed/.gitkeep
data/processed/pubmed/.gitkeep
```

后续真实运行时：

- PubMed 原始 API 响应保存到 `data/raw/pubmed/`。
- PubMed 清洗结果保存到 `data/processed/pubmed/`。
- 生成数据不提交 Git。
- 只提交 `.gitkeep` 作为目录占位。

## 5. `.gitignore` 确认

当前规则要求：

- 忽略虚拟环境 `literature_env/`。
- 忽略 `.env` 和本地密钥文件。
- 忽略 Python 缓存和 pytest 缓存。
- 忽略构建产物。
- 忽略 `data/raw/` 和 `data/processed/` 下的生成数据。
- 允许追踪：
  - `data/raw/.gitkeep`
  - `data/processed/.gitkeep`
  - `data/raw/pubmed/.gitkeep`
  - `data/processed/pubmed/.gitkeep`

## 6. 测试边界确认

本轮测试不访问真实网络。

含义：

```text
真实运行程序：可以访问 PubMed。
自动化测试：不得访问 PubMed，必须使用 mock HTTP response。
```

这样做是为了：

- 避免测试受网络波动影响。
- 避免依赖 PubMed 服务实时状态。
- 避免触发接口频率限制。
- 可以稳定模拟 429、5xx、timeout、空结果和异常 XML。
- 确认代码逻辑正确，而不是测试外部网站是否可用。

## 7. 阶段 1 产出

本阶段产出：

- 确认第一轮只做 PubMed 单源主链路。
- 确认不加入 LLM、邮件发送、数据库、网页和多数据源。
- 确认当前包名和 `src` 项目结构。
- 确认 OpenAlex 已有功能不应被破坏。
- 新增 PubMed raw 和 processed 目录占位。
- 调整 `.gitignore`，确保 PubMed 生成数据不被提交。
- 明确测试中不得访问真实网络。

## 8. 阶段 1 验收结论

阶段 1 已完成。

可以进入阶段 2：

```text
参数模型与 CLI 骨架
```

阶段 2 开始后，建议先新增：

- `src/scholarlead_agent/pubmed_models.py`
- `src/scholarlead_agent/pubmed_main.py`
- `tests/test_pubmed_models.py`
- `tests/test_pubmed_main.py`
