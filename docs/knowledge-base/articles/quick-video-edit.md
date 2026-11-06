---
id: "quick-video-edit"
title: "编辑或重新规划视频方案"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/workspace/quick/:runId?"]
source_refs: [{"path":"frontend/src/features/workspace/VideoTaskPanel.vue","line_start":52,"line_end":116},{"path":"frontend/src/features/workspace/VideoTaskPanel.vue","line_start":169,"line_end":177},{"path":"backend/app/tasks/media_routes.py","line_start":39,"line_end":84}]
deployment_status: "not_verified"
review_required: true
---

# 编辑或重新规划视频方案

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 可以修改分镜吗？
- 改完方案为什么不能马上确认？

## 简洁回答
待确认时可用“编辑方案”修改镜头文字与音乐方向，或用“重新生成方案”提出调整要求。先保存并完整读取新方案，再确认继续。

## 操作步骤
1. 点“编辑方案”，按需修改画面、动作、景别、运镜、字幕、旁白、音乐方向。
2. 点“保存方案”；也可点“确认方案”，有修改时会先保存。
3. 等新方案完整读取后，核对并完成确认弹窗。

## 常见异常及处理
新方案读取失败时用“重新读取”，不要确认旧方案。原操作未确认时用“核对并重试原操作”。重新规划的“调整要求”为选填，最多 9800 字；不要将重新规划方案与重新收费生成一条视频混为一谈。
