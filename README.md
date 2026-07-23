# Literature AI Agent

一个用于文献检索与分析的 Python 项目原型。

## 当前已实现

- 项目基础 `src` 目录结构
- OpenAlex Works API 论文采集
- OpenAlex `abstract_inverted_index` 摘要还原
- DOI 标准化与去重
- 原始 API 响应保存到 `data/raw`
- 清洗结果保存到 `data/processed`
- 清洗结果同时输出 JSON 和 CSV
- 命令行参数校验
- pytest 测试，测试中不访问真实网络

## 当前未实现

- Crossref
- LLM
- Streamlit
- 数据库
- 邮箱生成或发送
- 作者邮箱猜测

## 安装

使用当前虚拟环境：

```powershell
.\literature_env\Scripts\python.exe -m pip install -r requirements.txt
.\literature_env\Scripts\python.exe -m pip install -e .
```

## 运行 OpenAlex 采集

`max-results` 第一版最大为 20。

```powershell
.\literature_env\Scripts\python.exe -m literature_agent.main `
  --query "genome assembly" `
  --from-date 2024-01-01 `
  --to-date 2024-12-31 `
  --max-results 10
```

输出文件会写入：

- `data/raw`
- `data/processed`

文件名会包含检索关键词和时间戳。

## 运行测试

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

## 安全与数据规则

- 不在代码中保存密码或 API Key
- `.env` 不提交到 Git
- 原始 API 响应先保存，再清洗
- DOI 优先去重；没有 DOI 时使用 OpenAlex ID 去重
- 不猜测缺失的作者邮箱
- 不自动发送邮件
