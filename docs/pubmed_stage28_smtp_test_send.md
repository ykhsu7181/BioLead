# 阶段 28：真实测试邮件发送入口

日期：2026-08-25  
项目：ScholarLead Agent  
依据文档：`docs/pubmed_first_round_implementation_plan_v2.5.md`、`docs/pubmed_stage27_email_provider_decision.md`

---

## 1. 阶段目标

阶段 28 在现有邮件审核和发送权限边界上，新增第一版真实 SMTP 测试发送入口。

本阶段实现的是：

```text
approved 邮件草稿
-> 人工确认测试发送
-> 读取本地 .env SMTP 配置
-> 实际收件人替换为 EMAIL_TEST_RECIPIENT
-> SmtpEmailProvider 调用真实 SMTP
-> 返回 sent / failed / blocked
-> 写入 email_send_logs 和 email_audit
```

本阶段仍不实现：

```text
无人审核自动发送
批量群发
向真实客户 PI 默认发送
Agent 可调用 send_email Tool
失败后无限重试
```

---

## 2. 新增能力

### 2.1 本地 `.env` 自动读取

`load_config()` 现在会读取项目根目录下的 `.env`。

如果 PowerShell 已经设置同名环境变量，则环境变量优先，`.env` 不覆盖已有值。

### 2.2 SMTP 配置字段

`.env.example` 增加占位配置：

```text
EMAIL_PROVIDER=smtp
EMAIL_SEND_ENABLED=false
EMAIL_SENDER=your_sender@example.com
EMAIL_TEST_RECIPIENT=your_test_recipient@example.com
EMAIL_ALLOWED_RECIPIENTS=your_test_recipient@example.com
EMAIL_DAILY_LIMIT=5

SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USERNAME=your_sender@example.com
SMTP_PASSWORD=
SMTP_USE_SSL=true
SMTP_TIMEOUT_SECONDS=30
```

真实授权码只允许放在本地 `.env`，不能写入代码、README、docs 或测试。

### 2.3 SMTP Provider

新增 `SmtpEmailProvider`：

```text
src/scholarlead_agent/email_smtp.py
```

职责：

- 构造 SMTP 邮件；
- 使用 `smtplib.SMTP_SSL` 或 `smtplib.SMTP` 发送；
- 登录发件邮箱；
- 成功返回 `sent`；
- 失败返回 `failed` 和错误信息；
- 不记录 SMTP 授权码。

### 2.4 测试发送模式

第一版采用安全测试模式：

```text
邮件内容：基于真实 Lead / PI
原始 PI 邮箱：保留在 preview 中展示
实际收件人：EMAIL_TEST_RECIPIENT
```

这样可以验证真实 SMTP 发送链路，但不会直接打扰客户 PI。

### 2.5 Streamlit 发送入口

Streamlit 邮件草稿区域新增：

```text
测试邮件发送 / Test email sending
```

页面会展示：

- 原始 PI 邮箱；
- 实际测试收件邮箱；
- 发件账号；
- provider；
- 是否启用真实发送；
- 每日限制；
- blockers；
- 人工确认勾选框；
- 发送测试邮件按钮；
- sent / failed / blocked 结果。

只有用户勾选确认后，按钮才可点击。

---

## 3. 安全规则

发送前必须满足：

```text
EMAIL_PROVIDER=smtp
EMAIL_SEND_ENABLED=true
SMTP 配置完整
EMAIL_TEST_RECIPIENT 已配置
EMAIL_TEST_RECIPIENT 在 EMAIL_ALLOWED_RECIPIENTS 中
EMAIL_DAILY_LIMIT > 0
草稿状态为 review_approved
存在 verified_email
存在 human_reviewer / reviewed_at
subject / body 非空
```

否则结果为：

```text
blocked
```

失败不会自动无限重试，只记录：

```text
failed
```

---

## 4. 本地 `.env` 示例

如果使用 Yeah / 网易邮箱，示例：

```text
EMAIL_PROVIDER=smtp
EMAIL_SEND_ENABLED=true
EMAIL_SENDER=agent_test@yeah.net
EMAIL_TEST_RECIPIENT=your_test_recipient@qq.com
EMAIL_ALLOWED_RECIPIENTS=your_test_recipient@qq.com
EMAIL_DAILY_LIMIT=5

SMTP_HOST=smtp.yeah.net
SMTP_PORT=465
SMTP_USERNAME=agent_test@yeah.net
SMTP_PASSWORD=your_smtp_authorization_code
SMTP_USE_SSL=true
SMTP_TIMEOUT_SECONDS=30
```

注意：

- `SMTP_HOST` 前后不要加空格；
- `SMTP_PASSWORD` 是授权码，不是网页登录密码；
- `EMAIL_SEND_ENABLED=false` 时不会真实发送；
- `smtp.yeah.net` 是程序连接的服务器地址，不是网页地址，浏览器打不开是正常的。

---

## 5. 人工 smoke test 步骤

1. 确认 `.env` 已填写 SMTP 配置；
2. 确认 `EMAIL_SEND_ENABLED=true`；
3. 确认 `EMAIL_TEST_RECIPIENT` 是自己的测试邮箱；
4. 确认 `EMAIL_ALLOWED_RECIPIENTS` 包含该测试邮箱；
5. 启动 Streamlit：

```powershell
cd "D:\ScholarLead Agent"
.\literature_env\Scripts\python.exe -m streamlit run src\scholarlead_agent\ui\streamlit_app.py
```

6. 运行 PubMed 小范围任务；
7. 选择有 verified email 的 Lead；
8. 生成邮件草稿；
9. 保存人工审核为 approve；
10. 在测试发送区勾选确认；
11. 点击发送测试邮件；
12. 检查测试邮箱是否收到邮件；
13. 检查页面结果为 `sent` 或 `failed`；
14. 检查 SQLite `email_send_logs` 是否记录发送结果。

---

## 6. 新增和修改文件

新增：

```text
src/scholarlead_agent/email_smtp.py
changes: SmtpEmailProvider / SMTP config builder / test send wrapper / preview helper

tests/test_email_smtp.py
changes: Fake SMTP tests, no real network or real mailbox access
```

修改：

```text
src/scholarlead_agent/config.py
changes: project .env loading and SMTP/email config fields

src/scholarlead_agent/email_sending.py
changes: optional extra_blockers for Stage 28 safety checks; existing calls remain compatible

src/scholarlead_agent/ui/streamlit_app.py
changes: Streamlit manual test-send panel and email_send_logs writing

.env.example
changes: SMTP/email placeholder configuration only, no real secrets
```

---

## 7. 测试结果

局部测试：

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_email_smtp.py tests\test_email_sending.py tests\test_email_review.py tests\test_pubmed_ui.py
```

结果：

```text
37 passed
```

全量测试结果见最终汇报。

---

## 8. 已知限制

- 当前真实发送只建议用于自己的测试邮箱；
- 当前不会默认发送给真实 PI；
- 当前没有 Agent `send_email` Tool；
- 当前没有批量发送；
- 当前每日额度通过本地发送日志统计，适合第一版测试，不是生产级额度系统；
- SMTP 服务是否成功取决于邮箱服务、授权码和网络环境。

---

## 9. 验收结论

阶段 28 已实现第一版真实测试邮件发送入口。

达到：

```text
真实 SMTP Provider 可配置
默认不发送，必须 EMAIL_SEND_ENABLED=true
Streamlit 有人工确认发送入口
实际收件人限定为测试邮箱 / 白名单
发送结果可见
发送日志可写入 email_send_logs
pytest 不访问真实邮箱服务
```

本阶段完成后停止，不自动进入阶段 29。
