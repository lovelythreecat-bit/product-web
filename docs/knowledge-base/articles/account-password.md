---
id: "account-password"
title: "修改密码与无法登录时的处理"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/account","/login"]
source_refs: [{"path":"frontend/src/features/account/ChangePasswordDrawer.vue","line_start":19,"line_end":48},{"path":"backend/app/admin/user_management.py","line_start":237,"line_end":250},{"path":"docs/电商AI创作平台-首版需求终稿-2026-10-09.md","line_start":382,"line_end":382}]
deployment_status: "not_verified"
review_required: true
---

# 修改密码与无法登录时的处理

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 怎么改密码？
- 忘记密码能找回吗？

## 简洁回答
已登录且知道当前密码时，在个人中心“修改密码”，填写当前密码、新密码和确认新密码，点“确认修改”。新密码 10–128 个字符，不能与当前密码相同，两次新密码需一致。成功后所有设备需重新登录。

## 何时需要人工帮助
忘记当前密码或无法登录时，请工作人员核验身份后协助。管理员重置已有代码，但不承诺无需核验、立即恢复或固定处理时间；对外联系渠道本次未确认。不要发送密码、验证码或完整身份材料。
