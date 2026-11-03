---
id: "works-download"
title: "预览、复制和下载作品"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/works","/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/components/ResultViewer.vue","line_start":14,"line_end":29},{"path":"frontend/src/components/ResultViewer.vue","line_start":45,"line_end":69},{"path":"frontend/src/features/works/WorksView.vue","line_start":65,"line_end":65}]
deployment_status: "not_verified"
review_required: true
---

# 预览、复制和下载作品

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 三张详情图怎么下载？
- 文案在哪里复制？

## 简洁回答
我的作品中图片、视频可预览和下载。单文件点“下载”；多文件在下载菜单选对应文件或“下载全部”，触屏可点击展开。下载全部是逐文件下载，不保证压缩包。

## 常见异常及处理
我的作品文案卡片主要提供“复制文案”，不展示图片视频同样的下载、预览入口。复制失败可手动选择文字。图片视频下载失败先核对登录和可访问状态，持续失败转人工，不重新生成代替下载。
