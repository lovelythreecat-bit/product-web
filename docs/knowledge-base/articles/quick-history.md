---
id: "quick-history"
title: "查看图片和文案历史版本"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/quick-generation/QuickImageHistory.vue","line_start":12,"line_end":43},{"path":"frontend/src/features/quick-generation/QuickCopyHistory.vue","line_start":14,"line_end":43},{"path":"backend/app/quick_generation/service.py","line_start":191,"line_end":205}]
deployment_status: "not_verified"
review_required: true
---

# 查看图片和文案历史版本

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 图片重做后旧版在哪里？
- 为什么文案历史是空的？

## 简洁回答
图片对应类型旁的“历史版本”展示该类型重生成前的成功版本，排除当前版及重复项；详情图以完整三张一组展示。历史只读，可预览、下载。

## 常见异常及处理
没有旧版本时显示空状态。文案也有历史版本入口，但代码核对发现旧文案任务未被流程读取接口完整返回的风险，不能保证所有旧文案都能在此恢复。可先到我的作品核对原成果，仍找不到时转人工。

## 审核提示
文案历史存在前后端覆盖差异，验证或修复后再作为完整功能说明导入。
