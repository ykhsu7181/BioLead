# PubMed 阶段 16：README 与配置示例更新

## 1. 本阶段目标

阶段 16 的目标是让项目文档和当前 PubMed 第一轮代码状态保持一致，并明确说明第一轮的运行方法、输出文件、测试命令、已实现能力和未实现边界。

本阶段只更新文档和 `.env.example`，不进入阶段 17。

## 2. 本阶段修改文件

```text
README.md
README_cn.md
.env.example
docs/pubmed_stage16_readme_config_update.md
```

## 3. README.md 更新内容

英文 README 已更新为当前阶段 15 后的状态，重点说明：

```text
PubMed 第一轮定位
安装和环境
NCBI 环境变量
PubMed CLI 运行命令
输入参数说明
raw 输出文件
processed 输出文件
run report
测试命令
第一轮已实现能力
第一轮未实现能力
PubMed 临时评分不是正式四维评分
第一轮不使用 LLM
第一轮不是完整 Agent 交付
第一轮不是 T+45 或最终验收
```

## 4. README_cn.md 更新内容

中文版 README 已重写，修复原有乱码问题，并和英文 README 保持同一口径。

重点说明：

```text
当前第一轮是 PubMed 单源内部验证链路
测试中不访问真实网络
真实运行 CLI 会访问 PubMed
邮箱只从 PubMed affiliation 中提取
候选 PI 不等于已确认通讯作者
临时评分不等于正式四维评分
当前不生成邮件、不发送邮件、不接入 LLM
```

## 5. .env.example 更新内容

`.env.example` 只保留 NCBI 相关占位配置：

```text
NCBI_TOOL=ScholarLeadAgent
NCBI_EMAIL=your.email@example.com
NCBI_API_KEY=
```

说明：

```text
1. 不提交真实凭证
2. NCBI_API_KEY 第一轮可以为空
3. 真实配置放在本地 .env 或环境变量中
```

## 6. 当前 PubMed CLI 命令

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main `
  --query "single-cell RNA sequencing cancer" `
  --from-date 2024-01-01 `
  --to-date 2024-12-31 `
  --max-results 10 `
  --country us `
  --service-type scRNA-seq
```

## 7. 当前测试命令

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

## 8. 测试结果

阶段 16 完成后运行全量测试：

```text
112 passed
```

## 9. 本阶段不做什么

```text
不修改 PubMed 主链路代码
不接入 LLM
不接入 Agent Loop
不接入 Crossref
不接入基金源
不新增数据库
不实现前端
不生成邮件
不发送邮件
不进入阶段 17
```

## 10. 验收结论

阶段 16 已完成：

```text
README.md 已更新
README_cn.md 已更新并修复乱码
.env.example 已更新为 NCBI 占位配置
PubMed 第一轮运行方法已写明
raw / processed / run report 输出已写明
临时评分边界已写明
未实现能力边界已写明
全量 pytest 通过
```
