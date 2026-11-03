---
id: "quick-recovery"
title: "任务核查、保存恢复与成果读取失败"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/components/TaskCard.vue","line_start":70,"line_end":83},{"path":"frontend/src/components/TaskCard.vue","line_start":108,"line_end":113},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":367,"line_end":369},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":412,"line_end":429},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":24,"line_end":46},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":318,"line_end":344},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":412,"line_end":438},{"path":"docs/电商AI创作平台-首版需求终稿-2026-10-09.md","line_start":201,"line_end":207},{"path":"docs/电商AI创作平台-首版需求终稿-2026-10-09.md","line_start":382,"line_end":384},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":78,"line_end":83}]
deployment_status: "not_verified"
review_required: true
---

# 任务核查、保存恢复与成果读取失败

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 恢复原结果时要重新生成吗？
- 成功了为什么看不到作品？

## 简洁回答
待核查、结果保存中、保存失败待恢复不能直接当作生成失败。查看原任务，等待核查或恢复原结果，不要为了读取成果重新付费生成。

## 操作步骤
显示作品暂时无法读取时点“重新读取作品”，也可到我的作品核对。无法自动复制时选择文案手动复制。

## 常见异常及处理
任务全部结束后停止自动读取进度可能是正常行为，不必因此新建任务。费用和结算以最新业务结果为准。

## 何时需要人工帮助
持续核查、保存无法恢复、成果链接失效或状态矛盾时交人工，不承诺退款、补偿或自动释放时间。
