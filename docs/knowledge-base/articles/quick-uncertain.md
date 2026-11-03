---
id: "quick-uncertain"
title: "提交超时或结果尚未确认"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":284,"line_end":307},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":138,"line_end":138},{"path":"backend/app/quick_generation/service.py","line_start":406,"line_end":417},{"path":"backend/app/quick_generation/service.py","line_start":466,"line_end":475},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":24,"line_end":46},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":318,"line_end":344},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":412,"line_end":438}]
deployment_status: "not_verified"
review_required: true
---

# 提交超时或结果尚未确认

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 生成超时了，要再开一单吗？
- 网络断了是不是没扣积分？

## 简洁回答
先核对原请求，不要重新创建收费任务。页面保留原费用批次，提供“核对原批次费用”，确认按钮可能显示“核对原批次”。

## 操作步骤
1. 保留流程，查看原批次和任务进度。
2. 用页面核对入口继续处理同一批次。
3. 根据业务接口的任务与积分状态判断结果。

## 常见异常及处理
超时不证明失败或成功。刷新、关闭页面不会取消后台任务。没有明确拒绝回执时，不承诺没有冻结或扣费。

## 何时需要人工帮助
持续无法核对时提供阶段、操作时间、必要错误，请工作人员查看原任务。
