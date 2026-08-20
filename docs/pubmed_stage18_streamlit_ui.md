# PubMed 第一轮阶段 18：轻量前端可视化展示

日期：2026-08-19

## 1. 阶段目标

阶段 18 只新增一个轻量 Streamlit 操作界面，用于内部演示和人工查看 PubMed 第一轮结果。

本阶段不是正式 CRM，不做登录、权限、多用户、数据库、LLM、Agent Loop 或真实邮件发送。

## 2. 本阶段新增内容

- 新增 Streamlit 页面入口：`src/scholarlead_agent/ui/streamlit_app.py`
- 新增 UI helper 测试：`tests/test_pubmed_ui.py`
- 更新依赖：`requirements.txt` 和 `pyproject.toml`
- 更新 README / README_cn 中的 Streamlit 启动方法

## 3. 页面能力

页面可以：

- 展示当前第一轮已实现和未实现能力；
- 输入 PubMed 检索参数；
- 调用已有 `run_pubmed_search(...)` 业务入口；
- 展示任务执行摘要；
- 展示 Papers 表；
- 展示 Leads 表；
- 按 country / priority / email_status 基础筛选 Leads；
- 查看单条 Lead 详情；
- 查看 Run Report；
- 下载 storage 层已经生成的 CSV / JSON / Run Report 文件。

## 4. 复用关系

Streamlit UI 只负责展示和交互。

实际 PubMed 主链路仍由以下模块负责：

- `pubmed_client.py`
- `pubmed_parser.py`
- `pubmed_leads.py`
- `pubmed_affiliation.py`
- `pubmed_scoring.py`
- `pubmed_storage.py`
- `services/pubmed_service.py`

UI 不复制采集、解析、评分、导出逻辑。

## 5. 启动命令

在项目根目录运行：

```powershell
.\literature_env\Scripts\python.exe -m streamlit run src\scholarlead_agent\ui\streamlit_app.py
```

页面中点击运行 PubMed 检索会访问真实 PubMed API。建议第一次把 `max_results` 设为 3 或 5。

## 6. 测试策略

UI 测试不访问真实 PubMed。

本阶段只测试可独立调用的 UI helper：

- 任务摘要字段转换；
- Papers 表格字段转换；
- Leads 表格字段转换；
- Leads 基础筛选。

## 7. 验收状态

已完成。

验证结果：

- UI helper 测试：`4 passed`
- 全量 pytest：`116 passed`
- Streamlit 本地页面：`http://localhost:8501` 返回 `200`

## 8. 已知限制

- 第一版页面偏演示用途，不是生产级后台；
- 只展示本次运行的结果，不做历史任务管理；
- 不提供登录、权限、CRM 或销售跟进；
- 不生成 AI 邮件；
- 不发送真实邮件；
- 不接入数据库。
