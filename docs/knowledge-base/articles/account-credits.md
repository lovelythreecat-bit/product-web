---
id: "account-credits"
title: "查看可用积分、冻结积分和流水"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/account","/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/account/AccountView.vue","line_start":179,"line_end":193},{"path":"frontend/src/features/account/AccountView.vue","line_start":210,"line_end":210},{"path":"backend/app/ledger/routes.py","line_start":1,"line_end":34},{"path":"frontend/src/components/TaskCard.vue","line_start":36,"line_end":66},{"path":"frontend/src/components/TaskCard.vue","line_start":98,"line_end":120},{"path":"backend/app/tasks/failed_actions.py","line_start":28,"line_end":69},{"path":"backend/app/tasks/failed_actions.py","line_start":97,"line_end":130},{"path":"backend/app/tasks/state_machine.py","line_start":166,"line_end":168},{"path":"backend/app/catalog/service.py","line_start":464,"line_end":542},{"path":"backend/app/tasks/admission.py","line_start":106,"line_end":126},{"path":"backend/app/tasks/admission.py","line_start":250,"line_end":251},{"path":"backend/app/quick_generation/service.py","line_start":406,"line_end":438},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":87,"line_end":89}]
deployment_status: "not_verified"
review_required: true
---

# 查看可用积分、冻结积分和流水

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 积分去哪了？
- 冻结是不是已经扣了？

## 简洁回答
个人中心积分账户显示可用、冻结、累计消费。冻结是预留，不能等同已消费，要同时看任务状态和结算状态。

## 操作步骤
1. 打开个人中心“积分账户”。
2. 在“积分流水”按开始日期、结束日期查询，或点“刷新记录”。
3. 点“查看详情”，核对数量、关联任务、变更前后余额与说明。

## 常见异常及处理
失败任务可能仍冻结，按任务可用操作处理。余额读取失败先刷新，不把空白或旧余额当实时结果。

## 何时需要人工帮助
流水无法对应、疑似重复扣费或状态矛盾时请工作人员核查，不自行承诺返还。
