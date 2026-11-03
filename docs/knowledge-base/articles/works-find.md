---
id: "works-find"
title: "查询和查看我的作品"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/works"]
source_refs: [{"path":"frontend/src/features/works/WorksView.vue","line_start":15,"line_end":40},{"path":"frontend/src/features/works/WorksView.vue","line_start":58,"line_end":74},{"path":"backend/app/works/service.py","line_start":46,"line_end":80}]
deployment_status: "not_verified"
review_required: true
---

# 查询和查看我的作品

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 作品在哪里？
- 列表为什么没有生成结果？

## 简洁回答
进入“我的作品”，按全部、文案、图片、视频筛选，输入商品名称后点“查询”。每页 10 条，可翻页；“重置”清除查询条件，“刷新作品”重新读取。

## 常见异常及处理
只有成功且已消费结算、未删除的可访问作品进入列表。生成、保存、核查或结算中可能尚未出现。先核对账号、筛选条件和原任务，不能直接认定丢失。

## 操作步骤
点“任务详情”查看状态、积分结算、原报价与“查看来源任务”。
