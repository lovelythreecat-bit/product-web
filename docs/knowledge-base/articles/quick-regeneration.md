---
id: "quick-regeneration"
title: "文案与图片的单项重新生成"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"backend/app/quick_generation/service.py","line_start":299,"line_end":325},{"path":"backend/app/quick_generation/service.py","line_start":425,"line_end":432},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":85,"line_end":85},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":123,"line_end":130},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":164,"line_end":171},{"path":"backend/app/catalog/service.py","line_start":464,"line_end":542},{"path":"backend/app/tasks/admission.py","line_start":106,"line_end":126},{"path":"backend/app/tasks/admission.py","line_start":250,"line_end":251},{"path":"backend/app/quick_generation/service.py","line_start":406,"line_end":438},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":87,"line_end":89}]
deployment_status: "not_verified"
review_required: true
---

# 文案与图片的单项重新生成

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 重新生成免费吗？
- 详情图能只重做一张吗？

## 简洁回答
当前快速生成对已完成文案或图片的对应单项重新生成记录免费次数，前三次免费，用完后重新确认费用。详情图按完整 3 张一组重新生成，不能只重做其中一张。

## 前置条件
流程尚未完成，所选项目成功并结算，其他任务没有阻塞；以该项实时剩余次数与费用确认结果为准。

## 常见异常及处理
重新选择文案类型、失败重试、释放后重新生成此项，与成功项目的单项重新生成不同，不能一律说免费。视频不适用这里的前三次免费。流程完成后只读。

## 审核提示
生产开放状态、计次范围和现行政策仍需确认，不把本地常量当作永久优惠承诺。
