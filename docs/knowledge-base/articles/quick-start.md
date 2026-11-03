---
id: "quick-start"
title: "开始或继续快速生成"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/router.ts","line_start":22,"line_end":29},{"path":"frontend/src/features/workspace/ConversationList.vue","line_start":176,"line_end":192},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":205,"line_end":230},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":195,"line_end":203},{"path":"backend/app/quick_generation/service.py","line_start":477,"line_end":515}]
deployment_status: "not_verified"
review_required: true
---

# 开始或继续快速生成

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 快速生成从哪里开始？
- 上次做到一半，怎么继续？

## 简洁回答
登录后进入工作台的“快速生成”。依次完成商品确认、营销文案、图片生成、视频生成，最后汇总成果。每阶段需要确认，不能跳过未完成阶段。

## 操作步骤
1. 选择“快速生成”；该入口会打开最近一条流程，没有记录时才创建新流程。
2. 要另做一件商品，点击侧栏“新建快速生成”。
3. 继续旧流程时，从侧栏选择对应记录；已完成记录只读。

## 前置条件
需要登录。生成服务和费用是否可用，以页面及实际提交结果为准。
