---
id: "quick-upload"
title: "上传商品参考图"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/workspace/materialLimits.ts","line_start":1,"line_end":2},{"path":"backend/app/common/types.py","line_start":12,"line_end":12},{"path":"frontend/src/features/quick-generation/QuickGenerationView.vue","line_start":111,"line_end":121},{"path":"frontend/src/features/quick-generation/useQuickGeneration.ts","line_start":351,"line_end":365},{"path":"backend/app/quick_generation/service.py","line_start":38,"line_end":40},{"path":"backend/app/storage/service.py","line_start":28,"line_end":57},{"path":"backend/app/quick_generation/schemas.py","line_start":15,"line_end":18}]
deployment_status: "not_verified"
review_required: true
---

# 上传商品参考图

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 能上传多少张商品图？
- 上传没结束，可以点下一步吗？
- 为什么图片传不上去？

## 简洁回答
当前本地前后端的新创作参考图上限为 4 张，支持 PNG、JPG、WebP。可多选或拖入图片，上传期间等待完成再继续；上传成功后还需要保存到本次流程。

## 操作步骤
1. 在商品参考图区选择或拖入图片。
2. 等待上传和保存完成，核对缩略图与错误提示。
3. 达到数量上限时，先移除不需要的引用，再添加图片。

## 常见异常及处理
格式不支持时换成支持的真实图片文件，不要只改扩展名。单文件大小受当前上传规则约束，不能把视频首帧的大小限制当作所有上传的统一承诺。错误后先确认哪些图片已经保存，避免重复添加。

## 审核提示
旧设计写 20 张，草稿结构也容纳 20 条，但新创作执行 4 张上限。正式导入前确认生产使用的规则。历史草稿可能保留更多引用，不代表还能按原数量新生成。
