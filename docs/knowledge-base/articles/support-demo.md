---
id: "support-demo"
title: "玲玲客服展示页的能力边界"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/ai-customer-service"]
source_refs: [{"path":"frontend/src/features/site/customer-service/CustomerServiceView.vue","line_start":15,"line_end":31},{"path":"frontend/src/features/site/customer-service/CustomerServiceView.vue","line_start":80,"line_end":96},{"path":"docs/product-design.md","line_start":13,"line_end":13}]
deployment_status: "not_verified"
review_required: true
---

# 玲玲客服展示页的能力边界

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 玲玲能看到我做到哪了吗？
- 会记住商品和偏好吗？

## 简洁回答
当前展示页是互动演示，只提供基础指引，尚未连接实时客服。“专属记忆”不能理解为已记住偏好或能读取其他页面的当前任务。

## 常见异常及处理
要具体指导时先说明当前步骤、按钮与必要提示，不要提供密码或完整商品资料。不能声称演示客服已替你提交、改动或核查任务。
