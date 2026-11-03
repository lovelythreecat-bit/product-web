---
id: "quick-product"
title: "填写并保存商品资料"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/quick-generation/QuickProductEditor.vue","line_start":20,"line_end":67},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":91,"line_end":91},{"path":"frontend/src/features/workspace/productTypes.ts","line_start":1,"line_end":34},{"path":"frontend/src/features/workspace/display.ts","line_start":2,"line_end":13},{"path":"backend/app/catalog/service.py","line_start":475,"line_end":485},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":195,"line_end":203},{"path":"backend/app/quick_generation/service.py","line_start":477,"line_end":515}]
deployment_status: "not_verified"
review_required: true
---

# 填写并保存商品资料

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 商品资料哪些必须填？
- 为什么商品确认过不去？

## 简洁回答
先填写“商品名称”、选择“商品类型”，再补齐当前页面标为必填的资料。必填项可能随当前创作能力变化，不能把所有规格字段都当成必填。

## 操作步骤
1. 在“商品确认”按真实商品填写基本信息、规格参数、卖点与使用场景。
2. 点击“保存商品资料”。“商品品类”未填写时，保存逻辑会使用所选商品类型名称补入；具体品类建议如实填写。
3. 点击“确认商品，生成文案”，打开文案创作要求。未保存的有效修改会先保存；这一步不是已经生成成功。

## 常见异常及处理
资料不完整时核对具体必填项。商品类型决定显示哪些规格字段，已有补充资料也可能需要填写。仅填完名称不保证满足后续图片、视频的要求。

## 何时需要人工帮助
必填提示与实际字段不一致、保存持续失败，请工作人员核对页面阶段和必要错误文字，不需要发送完整商品资料。
