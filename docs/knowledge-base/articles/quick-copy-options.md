---
id: "quick-copy-options"
title: "选择文案类型和创作要求"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/quick-generation/QuickCopyRequirements.vue","line_start":15,"line_end":45},{"path":"frontend/src/features/workspace/TextChoices.vue","line_start":24,"line_end":51},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":20,"line_end":21},{"path":"backend/app/quick_generation/schemas.py","line_start":11,"line_end":31},{"path":"backend/app/quick_generation/service.py","line_start":342,"line_end":386},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":195,"line_end":203},{"path":"backend/app/quick_generation/service.py","line_start":477,"line_end":515}]
deployment_status: "not_verified"
review_required: true
---

# 选择文案类型和创作要求

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 可以一次生成几种文案？
- 文案平台和语气在哪改？

## 简洁回答
“文案创作要求”可多选或自定义文案类型，最多 7 种，每种名称 1–100 个字符，至少一种。当前默认选中宣传文案、商品标题、卖点描述、详情介绍、社交平台文案、直播口播、营销策略。

## 操作步骤
1. 保留需要的文案类型。
2. 选择或填写“目标平台”“语气”；当前默认淘宝、自然，这两项未标为必填。
3. 核对积分，点击“确认生成文案”；费用变化时核对新的确认提示。

## 常见异常及处理
费用显示“—”不表示免费。当前弹窗不展示目标人群、最大字符数或额外协作要求，不要寻找这些输入框。
