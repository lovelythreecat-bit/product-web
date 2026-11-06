---
id: "quick-save-exit"
title: "保存退出与返回已到达步骤"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":24,"line_end":46},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":318,"line_end":344},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":412,"line_end":438},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":134,"line_end":156},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":138,"line_end":138},{"path":"backend/app/quick_generation/service.py","line_start":75,"line_end":100},{"path":"backend/app/quick_generation/service.py","line_start":257,"line_end":280},{"path":"frontend/src/router.ts","line_start":22,"line_end":29},{"path":"frontend/src/features/workspace/ConversationList.vue","line_start":176,"line_end":192},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":205,"line_end":230},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":19,"line_end":23},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":47,"line_end":55},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":51,"line_end":91}]
deployment_status: "not_verified"
review_required: true
---

# 保存退出与返回已到达步骤

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 生成时可以离开吗？
- 返回商品资料会取消任务吗？

## 简洁回答
已受理任务在后台继续。页面允许时点“保存并退出”，进入我的作品；之后从快速生成记录继续。查看已到达步骤不会取消其他阶段的任务。

## 常见异常及处理
上传或保存中先等待。未保存商品修改会先尝试保存，校验或保存失败可能阻止离开。关闭标签页不等于保存成功。

## 前置条件
导航仅可进入已经到达阶段，不能跳过未来步骤。任务处理中通常不能修改草稿，返回查看不等于可以编辑。
