---
id: "quick-conflict"
title: "进度冲突与修改后的重新确认"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":134,"line_end":156},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":138,"line_end":138},{"path":"backend/app/quick_generation/service.py","line_start":75,"line_end":100},{"path":"backend/app/quick_generation/service.py","line_start":257,"line_end":280}]
deployment_status: "not_verified"
review_required: true
---

# 进度冲突与修改后的重新确认

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 为什么提示其他窗口更新了进度？
- 改文案后为什么又要确认图片？

## 简洁回答
先自行保留需要的文字，再点“重新读取进度（放弃本页未保存修改）”；该操作会丢弃本页未保存修改。

## 常见异常及处理
修改商品资料或参考图会使后续确认失效；修改文案使图片、视频确认失效；修改图片选择影响后续视频。旧成果与费用记录保留，不会自动退积分或自动生成新成果。

## 何时需要人工帮助
读取后仍冲突，停止多窗口同时编辑并请工作人员核查。不要让客服自动覆盖本地文字。
