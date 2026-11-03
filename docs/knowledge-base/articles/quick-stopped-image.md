---
id: "quick-stopped-image"
title: "图片等待补充资料时能否重试"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/components/TaskCard.vue","line_start":36,"line_end":37},{"path":"frontend/src/components/TaskCard.vue","line_start":99,"line_end":120},{"path":"backend/app/tasks/stopped_image_retry.py","line_start":38,"line_end":89},{"path":"docs/product-design.md","line_start":53,"line_end":53}]
deployment_status: "not_verified"
review_required: true
---

# 图片等待补充资料时能否重试

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 图片等待补充资料怎么继续？
- 重试一定能出图吗？

## 简洁回答
只有页面为已停止且满足初步条件的图片任务提供“重试”时，才按该入口操作。系统还会核验原任务已停止、没有成果且未开始图片生成，核验通过才继续。

## 操作步骤
点对应任务“重试”，阅读“确认重试”说明再确认。它使用原资料，原资料不足时也可能再次停止。

## 常见异常及处理
无法确认安全重试时保留原任务和冻结积分，刷新进度核对。不能把视频补充资料入口套到图片任务，也不能保证所有待核查任务都可重试。

## 何时需要人工帮助
反复停止、需要修改但流程锁住或不清楚缺少哪些资料时，请工作人员核查。
