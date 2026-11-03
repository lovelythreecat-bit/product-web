---
id: "quick-fees"
title: "快速生成如何确认费用"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"backend/app/catalog/service.py","line_start":464,"line_end":542},{"path":"backend/app/tasks/admission.py","line_start":106,"line_end":126},{"path":"backend/app/tasks/admission.py","line_start":250,"line_end":251},{"path":"backend/app/quick_generation/service.py","line_start":406,"line_end":438},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":87,"line_end":89},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":284,"line_end":307},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":138,"line_end":138},{"path":"backend/app/quick_generation/service.py","line_start":406,"line_end":417},{"path":"backend/app/quick_generation/service.py","line_start":466,"line_end":475},{"path":"frontend/src/features/account/RechargeInfoView.vue","line_start":11,"line_end":18},{"path":"docs/电商AI创作平台-首版需求终稿-2026-10-09.md","line_start":209,"line_end":224}]
deployment_status: "not_verified"
review_required: true
---

# 快速生成如何确认费用

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 一整套生成多少钱？
- 详情图为什么比主图贵？
- 积分不足怎么办？

## 简洁回答
每阶段分别确认费用，没有统一固定的整套价格。当前代码按所选文案类型逐项计费；主图、长图各按一项图片报价，详情图按 3 张组成一项完整任务报价。准确积分以实时确认和任务记录为准。

## 操作步骤
1. 选择内容后等费用显示，再核对确认。
2. 新任务受理时冻结积分，完整成果保存成功后消费。
3. 不足时查看个人中心的可用与冻结积分；在线充值尚未开放。

## 常见异常及处理
报价变化时重新确认。只有明确提示任务未受理且业务接口确认拒绝时，才可说明没有新增任务与冻结；超时不能这样推断。取消未受理费用批次不会收费，不等于取消已受理任务。
