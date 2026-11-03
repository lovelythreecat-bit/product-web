---
id: "quick-video-frame"
title: "选择视频首帧并生成方案"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":169,"line_end":171},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":94,"line_end":119},{"path":"backend/app/quick_generation/service.py","line_start":215,"line_end":255},{"path":"backend/app/quick_generation/service.py","line_start":289,"line_end":292},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":195,"line_end":203},{"path":"backend/app/quick_generation/service.py","line_start":477,"line_end":515}]
deployment_status: "not_verified"
review_required: true
---

# 选择视频首帧并生成方案

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 视频首帧选哪张？
- 生成的图片可以做视频吗？

## 简洁回答
确认本次完整图片成果后，从商品参考图或本次已确认生成图片中选择一张可用首帧，再点“确认费用，生成视频方案”。不能直接使用任意其他任务的图片。

## 操作步骤
1. 进入“视频生成”，等待可选图片读取完成。
2. 选中首帧，核对视频费用并确认生成。
3. 等待方案，后续还需人工确认方案。

## 常见异常及处理
读取失败时点“重新读取图片”。首帧已删除、不可用或不支持时重新选择；当前首帧校验支持 PNG、JPG、WebP，文件大于 0 且不超过 20 MiB。未选择首帧时按钮可能仍可点击，但会提示补选；可点击不代表校验通过。
