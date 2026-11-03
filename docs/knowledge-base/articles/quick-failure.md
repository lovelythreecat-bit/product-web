---
id: "quick-failure"
title: "任务失败时重试或释放积分"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/components/TaskCard.vue","line_start":36,"line_end":66},{"path":"frontend/src/components/TaskCard.vue","line_start":98,"line_end":120},{"path":"backend/app/tasks/failed_actions.py","line_start":28,"line_end":69},{"path":"backend/app/tasks/failed_actions.py","line_start":97,"line_end":130},{"path":"backend/app/tasks/state_machine.py","line_start":166,"line_end":168},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":160,"line_end":165},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":211,"line_end":217},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":14,"line_end":19},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":239,"line_end":250},{"path":"backend/app/quick_generation/service.py","line_start":340,"line_end":347},{"path":"backend/app/quick_generation/service.py","line_start":505,"line_end":510}]
deployment_status: "not_verified"
review_required: true
---

# 任务失败时重试或释放积分

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 失败了为什么还冻结积分？
- 重试和重新生成有什么区别？

## 简洁回答
生成失败且积分仍冻结时，可选择“重试”或“释放积分”。重试使用原资料和原报价核验；释放将该任务冻结额度返还可用余额。不能仅凭失败二字判断积分已经退回。

## 操作步骤
1. 核对生成状态和积分结算状态。
2. 继续原内容时点“重试”，再“确认重试”。
3. 释放时点“释放积分”，再“确认释放积分”。
4. 用最新任务和流水核对结果；结果不明时点“重试原操作”。

## 常见异常及处理
原报价失效会保留冻结状态，可按提示释放后按新报价创作。图片失败项已释放时可见“重新生成此项”，须重新核对费用，不能沿用已释放额度。

## 何时需要人工帮助
没有适用按钮、状态矛盾或流水无法核对时交人工，不承诺返还时限。
