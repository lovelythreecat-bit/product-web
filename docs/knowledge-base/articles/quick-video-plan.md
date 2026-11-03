---
id: "quick-video-plan"
title: "查看并确认视频方案"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/workspace/VideoTaskPanel.vue","line_start":145,"line_end":177},{"path":"backend/app/tasks/media_routes.py","line_start":1,"line_end":30}]
deployment_status: "not_verified"
review_required: true
---

# 查看并确认视频方案

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 视频为什么一直等我确认？
- 确认方案还要再扣一次吗？

## 简洁回答
方案待确认时点“查看并确认方案”，阅读后点“确认此方案”，再点弹窗“确认并继续生成”。此确认沿用当前任务已冻结积分，不再次收费；完整成果保存后才消费。

## 前置条件
方案已完整读取，仍为当前待确认版本，没有未核对的原操作。

## 常见异常及处理
方案未完整读取或已更新时先刷新原任务、重新查看当前方案。等待确认期间积分保持冻结，不保证固定完成时间。

## 何时需要人工帮助
反复无法读取方案，或任务与费用状态矛盾时，请工作人员核查。
