---
id: "planned-context-service"
title: "规划中的页面感知客服"
status: "draft"
implementation_status: "planned"
applicable_routes: ["/ai-customer-service","/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/site/customer-service/CustomerServiceView.vue","line_start":15,"line_end":31},{"path":"frontend/src/features/site/customer-service/CustomerServiceView.vue","line_start":80,"line_end":96},{"path":"docs/product-design.md","line_start":13,"line_end":13}]
deployment_status: "not_verified"
review_required: true
---

# 规划中的页面感知客服

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 客服能直接看到缺少哪个必填项吗？

## 简洁回答
尚不能当作现有能力。后续拟用文章检索回答通用问题，用小范围图谱约束快速生成建议，再由前端提供最少页面状态。接口和上线范围待开发验收。

## 边界
本轮 Chroma、Neo4j 仅为资料组织目标，没有建立索引或连接服务。上下文契约为建议稿，不代表已有定位、高亮或自动操作能力。
