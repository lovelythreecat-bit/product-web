---
id: "quick-complete"
title: "完成汇总与只读查看"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":173,"line_end":203},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":51,"line_end":54},{"path":"backend/app/quick_generation/service.py","line_start":165,"line_end":167},{"path":"backend/app/quick_generation/service.py","line_start":511,"line_end":515},{"path":"frontend/src/router.ts","line_start":22,"line_end":29},{"path":"frontend/src/features/workspace/ConversationList.vue","line_start":176,"line_end":192},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":205,"line_end":230}]
deployment_status: "not_verified"
review_required: true
---

# 完成汇总与只读查看

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 视频完成后在哪里看全部成果？
- 已完成还能改吗？

## 简洁回答
视频成功保存并结算后点“完成并汇总成果”，查看已确认文案、图片与视频，再点“完成并查看作品”。流程完成后只读。

## 常见异常及处理
只读流程保留查看、复制、预览、下载和详情，不能修改资料、重新生成或再次确认。前面阶段的“下一步”用于浏览，视频阶段可“查看汇总”。要另做内容，点“新建快速生成”。
