---
id: "quick-images"
title: "选择图片内容并确认图片成果"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":160,"line_end":165},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":211,"line_end":217},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":14,"line_end":19},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":239,"line_end":250},{"path":"backend/app/quick_generation/service.py","line_start":340,"line_end":347},{"path":"backend/app/quick_generation/service.py","line_start":505,"line_end":510},{"path":"backend/app/catalog/service.py","line_start":464,"line_end":542},{"path":"backend/app/tasks/admission.py","line_start":106,"line_end":126},{"path":"backend/app/tasks/admission.py","line_start":250,"line_end":251},{"path":"backend/app/quick_generation/service.py","line_start":406,"line_end":438},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":87,"line_end":89},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":195,"line_end":203},{"path":"backend/app/quick_generation/service.py","line_start":477,"line_end":515}]
deployment_status: "not_verified"
review_required: true
---

# 选择图片内容并确认图片成果

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 如何生成详情图？
- 图片要全部做完才能进视频吗？

## 简洁回答
必须选择“目标平台”和至少一种图片内容。可选商品主图 1 张、详情图 3 张、商品长图 1 张；详情图作为完整一组处理。

## 操作步骤
1. 打开“选择图片内容”；初次进入图片阶段也可点“确认费用并生成图片”。
2. 从 Amazon、淘宝、天猫、京东、拼多多、Shopee、Lazada、SHEIN、Temu 中选一个平台。
3. 勾选图片类型，核对积分，点击“确认生成图片”。
4. 等本阶段所有任务成功并结算，预览后点“确认图片，继续视频”。

## 常见异常及处理
没有平台或图片类型时按提示补选。参考图和商品资料还须满足当前图片能力校验。部分成功时先处理失败或未完成项目，不能直接进入视频。快速生成当前没有白底图选项。
