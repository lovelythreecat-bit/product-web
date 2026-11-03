---
id: "unknown-self-recovery"
title: "待确认的自助找回与人工身份核验"
status: "draft"
implementation_status: "unknown"
applicable_routes: ["/login"]
source_refs: [{"path":"frontend/src/features/account/ChangePasswordDrawer.vue","line_start":19,"line_end":48},{"path":"backend/app/admin/user_management.py","line_start":237,"line_end":250},{"path":"docs/电商AI创作平台-首版需求终稿-2026-10-09.md","line_start":382,"line_end":382},{"path":"frontend/src/features/auth/AuthForm.vue","line_start":20,"line_end":55},{"path":"backend/app/auth/schemas.py","line_start":10,"line_end":17},{"path":"backend/app/auth/service.py","line_start":73,"line_end":123},{"path":"frontend/src/router.ts","line_start":44,"line_end":48}]
deployment_status: "not_verified"
review_required: true
---

# 待确认的自助找回与人工身份核验

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 可以用短信或邮箱找回密码吗？

## 简洁回答
本次未找到面向用户的短信或邮箱自助找回入口。管理员重置已有代码，但面向用户的身份核验办法、联系渠道与时限待确认。

## 边界
不进入默认导入集合，不要求用户向客服发送密码、验证码或完整身份证件。
