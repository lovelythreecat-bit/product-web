---
id: "support-human"
title: "哪些问题需要工作人员核查"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?","/login","/account","/works"]
source_refs: [{"path":"docs/电商AI创作平台-首版需求终稿-2026-10-09.md","line_start":201,"line_end":207},{"path":"docs/电商AI创作平台-首版需求终稿-2026-10-09.md","line_start":382,"line_end":384},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":78,"line_end":83},{"path":"frontend/src/features/account/ChangePasswordDrawer.vue","line_start":19,"line_end":48},{"path":"backend/app/admin/user_management.py","line_start":237,"line_end":250},{"path":"docs/电商AI创作平台-首版需求终稿-2026-10-09.md","line_start":382,"line_end":382},{"path":"frontend/src/components/TaskCard.vue","line_start":36,"line_end":66},{"path":"frontend/src/components/TaskCard.vue","line_start":98,"line_end":120},{"path":"backend/app/tasks/failed_actions.py","line_start":28,"line_end":69},{"path":"backend/app/tasks/failed_actions.py","line_start":97,"line_end":130},{"path":"backend/app/tasks/state_machine.py","line_start":166,"line_end":168}]
deployment_status: "not_verified"
review_required: true
---

# 哪些问题需要工作人员核查

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 一直卡住怎么办？
- 能保证多久退积分吗？

## 简洁回答
持续核查、保存无法恢复、疑似重复扣费、账号无法访问、作品误删或状态矛盾时，需要工作人员核查。当前资料未确认人工在线时间、联系渠道、时限或补偿规则。

## 建议准备的信息
说明页面、阶段、按钮、操作大致时间与必要错误。需定位任务时通过平台认可的安全渠道提供最少关联信息，不发送密码、密钥、完整聊天或商品资料。

## 常见异常及处理
没有实际转接能力时不能说“已转人工”或“工单已创建”。
