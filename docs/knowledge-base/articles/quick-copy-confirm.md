---
id: "quick-copy-confirm"
title: "确认营销文案后进入图片阶段"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":147,"line_end":158},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":198,"line_end":198},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":61,"line_end":85},{"path":"backend/app/quick_generation/service.py","line_start":483,"line_end":504},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":160,"line_end":165},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":211,"line_end":217},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":14,"line_end":19},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":239,"line_end":250},{"path":"backend/app/quick_generation/service.py","line_start":340,"line_end":347},{"path":"backend/app/quick_generation/service.py","line_start":505,"line_end":510},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":19,"line_end":23},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":47,"line_end":55},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":51,"line_end":91}]
deployment_status: "not_verified"
review_required: true
---

# 确认营销文案后进入图片阶段

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 文案出来了，下一步点哪里？
- 为什么“确认文案，生成图片”不能点？

## 简洁回答
等本阶段所有文案生成成功并完成结算后，核对并编辑内容。每一种已生成文案都必须保留非空内容，再点击“确认文案，生成图片”。

## 操作步骤
1. 检查各类文案，根据真实商品修改，不能把其中一项删成空白。
2. 点击“确认文案，生成图片”。
3. 在“选择图片内容”中选择平台和图片类型，再确认费用。

## 常见异常及处理
仍在生成、保存、结算或核查时，先查看任务状态。只看见文字不代表整个阶段可推进。“查看原始任务”可查看原任务状态。

## 前置条件
流程未完成、没有上传或其他正在处理的操作，也没有待核对提交或版本冲突。
