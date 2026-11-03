---
id: "account-login"
title: "账号注册与登录"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/login","/register"]
source_refs: [{"path":"frontend/src/features/auth/AuthForm.vue","line_start":20,"line_end":55},{"path":"backend/app/auth/schemas.py","line_start":10,"line_end":17},{"path":"backend/app/auth/service.py","line_start":73,"line_end":123},{"path":"frontend/src/router.ts","line_start":44,"line_end":48}]
deployment_status: "not_verified"
review_required: true
---

# 账号注册与登录

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 怎么注册？
- 为什么登录失败？

## 简洁回答
使用账号密码登录：账号 3–64 个字符，密码 10–128 个字符；注册需一致的确认密码，不要求手机或邮箱验证码。

## 操作步骤
1. 注册页填写账号、密码、确认密码，点“创建账号”。
2. 已有账号时切换“登录”，填写并提交。
3. 成功进入工作台；未登录访问受保护页面会转登录页。

## 常见异常及处理
两次密码不一致时重新确认。网络失败可重试当前操作；注册失败也可能是账号已使用，不能凭通用提示断定原因。赠送额度由当前配置决定，不承诺固定数量或重复赠送。

## 何时需要人工帮助
忘记密码、账号停用或持续无法登录时请平台工作人员核查，不要发送密码。
