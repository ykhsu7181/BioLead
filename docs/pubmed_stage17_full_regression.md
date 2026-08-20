# PubMed 阶段 17：完整测试与回归

## 1. 本阶段目标

阶段 17 的目标是确认 PubMed 第一轮阶段 1-16 的功能稳定，同时确认没有破坏已有 OpenAlex 能力。

本阶段只做检查、回归和记录，不新增业务功能。

## 2. 检查时间

```text
2026-08-19
```

## 3. 执行内容

本阶段完成了以下检查：

```text
1. 阅读 pubmed_first_round_implementation_plan_v2.md 中阶段 17 要求
2. 检查 git 当前状态
3. 检查 .gitignore 生成数据忽略规则
4. 检查 .env.example 是否只包含占位配置
5. 检查本地是否存在 .env
6. 运行 OpenAlex 回归测试
7. 运行 PubMed 分组测试
8. 运行全量 pytest
9. 检查 data/raw 和 data/processed 生成数据是否被忽略
10. 检查明显密钥、密码、token、SMTP 等敏感词
```

## 4. 测试命令和结果

### 4.1 OpenAlex 回归测试

命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_openalex_client.py tests\test_works.py tests\test_storage.py
```

结果：

```text
13 passed
```

### 4.2 PubMed 分组测试

命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_pubmed_client.py tests\test_pubmed_parser.py tests\test_pubmed_leads.py tests\test_pubmed_scoring.py tests\test_pubmed_storage.py tests\test_pubmed_main.py tests\test_pubmed_models.py
```

结果：

```text
98 passed
```

### 4.3 全量测试

命令：

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

结果：

```text
112 passed
```

## 5. 生成数据检查

已确认真实运行生成的数据被 `.gitignore` 忽略。

忽略范围包括：

```text
data/raw/*
data/processed/*
data/raw/pubmed/*
data/processed/pubmed/*
```

保留目录占位：

```text
data/raw/.gitkeep
data/processed/.gitkeep
data/raw/pubmed/.gitkeep
data/processed/pubmed/.gitkeep
```

## 6. 配置和凭证检查

`.env.example` 当前只包含占位配置：

```text
NCBI_TOOL=ScholarLeadAgent
NCBI_EMAIL=your.email@example.com
NCBI_API_KEY=
```

检查结果：

```text
未发现本地 .env 文件
未发现真实 API Key
未发现真实密码
未发现 SMTP 凭证
未发现 OAuth token
```

说明：

```text
tests/test_pubmed_client.py 中的 test-key 是单元测试用假值
README / docs 中的 NCBI_API_KEY 是占位说明
```

## 7. 当前 git 状态

阶段 17 执行前，工作区只有一个未跟踪 PDF 需求书文件：

```text
海外Agent需求与验收标准-细化.pdf
```

该文件未纳入代码提交。

阶段 17 新增本记录文档：

```text
docs/pubmed_stage17_full_regression.md
```

## 8. 回归结论

阶段 17 通过：

```text
OpenAlex 回归测试通过
PubMed 分组测试通过
全量 pytest 通过
README / README_cn / .env.example 与当前代码状态一致
临时评分标识正确
无 LLM 调用
无 Agent Loop
无真实邮件发送
生成数据已被忽略
未发现真实凭证提交风险
```

## 9. 已知限制

```text
1. 当前仍是 PubMed 单源第一轮
2. 当前没有正式四维评分
3. 当前没有 Crossref / 基金源 / ORCID
4. 当前没有前端页面
5. 当前没有 LLM / Agent Loop
6. 当前没有邮件草稿生成和真实发送
7. 未跟踪 PDF 需求书仍留在工作区，未纳入 git
```

## 10. 下一阶段

下一阶段是：

```text
阶段 18：轻量 Streamlit 可视化展示
```

需要单独确认后再开始，不在阶段 17 中执行。
