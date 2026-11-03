---
id: "works-delete"
title: "删除作品的后果"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/works"]
source_refs: [{"path":"frontend/src/features/works/WorksView.vue","line_start":77,"line_end":77},{"path":"backend/app/works/lifecycle.py","line_start":28,"line_end":34},{"path":"backend/app/works/lifecycle.py","line_start":94,"line_end":159}]
deployment_status: "not_verified"
review_required: true
---

# 删除作品的后果

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 删除会退积分吗？
- 旧下载链接还能用吗？

## 简洁回答
点击“删除作品”并确认后，作品与原下载链接不可访问，来源任务与积分记录保留。删除不是退款或取消生成，不承诺恢复或返还消费积分。

## 前置条件
须有适用删除政策；提示缺少政策时不能删除。

## 何时需要人工帮助
误删、需要恢复或删除状态不明时请工作人员核查，不承诺回收站、恢复期限或立即释放空间。
