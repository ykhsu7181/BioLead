# 阶段 27：真实邮件 Provider 接入方案确认

日期：2026-08-25  
项目：ScholarLead Agent  
依据文档：`docs/pubmed_first_round_implementation_plan_v2.5.md`

---

## 1. 阶段目标

阶段 27 的目标是在开发真实邮件发送代码之前，先确认第一版真实邮件发送方案。

本阶段只做方案确认和配置占位，不实现 SMTP 发送代码，不开放前端真实发送按钮，不注册 Agent `send_email` Tool。

---

## 2. 已确认方案

第一版真实邮件测试方案如下：

```text
邮箱服务：网易个人测试邮箱
发送方式：SMTP
发件邮箱：个人测试网易邮箱
收件范围：QQ 邮箱或其他个人测试邮箱
禁止发送对象：真实客户 PI
发送数量限制：第一版限制 1～5 封
邮件签名：暂不需要
退订说明：暂不需要
失败处理：不自动无限重试，只记录 failed
SMTP 授权码：已有，只放本地 .env，不写入代码和文档
```

---

## 3. 为什么需要 SMTP / 邮箱服务

ScholarLead Agent 自身不能独立完成邮件投递。真实邮件必须通过邮箱系统或邮件服务发送。

本项目负责：

```text
生成邮件草稿
-> 人工审核
-> 权限检查
-> 调用 EmailProvider
-> 记录 sent / failed / blocked
```

网易邮箱负责：

```text
认证发件账号
-> 接收 SMTP 请求
-> 投递邮件
-> 返回发送结果或错误
```

---

## 4. 第一版配置口径

`.env.example` 只放占位字段，不放真实邮箱和授权码。

本地 `.env` 后续可按以下方式填写：

```text
EMAIL_PROVIDER=smtp
EMAIL_SEND_ENABLED=true
EMAIL_SENDER=your_163_test_email@163.com
EMAIL_TEST_RECIPIENT=your_test_recipient@qq.com
EMAIL_ALLOWED_RECIPIENTS=your_test_recipient@qq.com,another_test@example.com
EMAIL_DAILY_LIMIT=5

SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USERNAME=your_163_test_email@163.com
SMTP_PASSWORD=your_163_smtp_authorization_code
SMTP_USE_SSL=true
SMTP_TIMEOUT_SECONDS=30
```

注意：

- `SMTP_PASSWORD` 使用网易客户端授权码，不使用网页登录密码；
- `.env` 不提交 git；
- 授权码不写进 README、docs、测试或日志；
- 第一版建议只允许发到测试邮箱或白名单邮箱。

---

## 5. 阶段 28 开发前置条件

阶段 28 可以基于本方案实现真实测试邮件发送入口。

进入阶段 28 前需满足：

```text
网易 SMTP 授权码已准备
本地 .env 已配置
测试收件邮箱已确认
EMAIL_ALLOWED_RECIPIENTS 白名单已确认
EMAIL_DAILY_LIMIT 设置为 1～5
确认不发送给真实客户 PI
```

---

## 6. 阶段 28 建议实现边界

下一阶段建议实现：

```text
SmtpEmailProvider
SMTP 配置读取
发送启用开关 EMAIL_SEND_ENABLED
测试收件人白名单
每日发送上限
Streamlit 人工确认发送入口
发送结果写入 email_send_logs
```

仍然禁止：

```text
无人审核自动发送
批量群发
Agent 直接调用 send_email
向真实客户 PI 默认发送
失败后无限重试
记录 SMTP 授权码
```

---

## 7. 测试策略

自动化测试仍然不得访问真实邮箱系统。

pytest 中应使用 Fake SMTP / Fake Provider，覆盖：

```text
EMAIL_SEND_ENABLED=false -> blocked
SMTP 配置缺失 -> blocked
未 approved -> blocked
无 verified email -> blocked
非白名单收件人 -> blocked
Fake SMTP 成功 -> sent
Fake SMTP 失败 -> failed
发送日志写入 email_send_logs
```

真实网易邮箱发送只作为人工 smoke test，在本地 `.env` 明确配置后执行。

---

## 8. 验收结论

阶段 27 已确认：

```text
Provider = 网易个人测试邮箱
Protocol = SMTP
Scope = 单封 / 小范围测试邮箱
Limit = 1～5 封
No real PI sending = true
No signature / unsubscribe in first version = true
Failure handling = record failed only
Secrets in code/docs = false
```

阶段 27 验收通过。

本阶段到此停止，不自动开始阶段 28。
