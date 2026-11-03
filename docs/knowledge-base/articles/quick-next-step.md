---
id: "quick-next-step"
title: "下一步按钮不可用时怎么判断"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":195,"line_end":203},{"path":"backend/app/quick_generation/service.py","line_start":477,"line_end":515},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":147,"line_end":158},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":198,"line_end":198},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":61,"line_end":85},{"path":"backend/app/quick_generation/service.py","line_start":483,"line_end":504},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":24,"line_end":46},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":318,"line_end":344},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":412,"line_end":438},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":284,"line_end":307},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":138,"line_end":138},{"path":"backend/app/quick_generation/service.py","line_start":406,"line_end":417},{"path":"backend/app/quick_generation/service.py","line_start":466,"line_end":475}]
deployment_status: "not_verified"
review_required: true
---

# 下一步按钮不可用时怎么判断

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 下一步灰色怎么回事？
- 我该点哪个按钮？

## 简洁回答
需要当前步骤、按钮名称和实际阻塞状态才能判断。灰色不一定是少填资料，上传、任务运行、结算未完成、冲突或提交待核对都可能阻止操作。

## 操作步骤
1. 上传或保存时等待当前操作完成。
2. 任务未完成时查看状态；失败则按可用的重试或释放入口处理。
3. 文案阶段须全部成功并结算，且每种文案非空；图片、视频须本阶段全部成功并结算。
4. 缺少状态时先问：你现在在哪一步、哪个按钮不可用，页面显示什么提示？

## 前置条件
导航的“上一步”“下一步”也可能只是查看已到达阶段，不代表重新确认或新建任务。不能仅靠步骤名称推断可执行操作。
