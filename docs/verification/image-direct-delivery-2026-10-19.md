# 图片生成直接交付

用户要求取消图片 Agent 的生成后审核，生成成功后直接返回。

## 当前行为

- 商品主图、详情组图、白底图和商品长图的新任务默认直接交付；生成后不调用画面审核、商品一致性复核、详情组图审核或长图文案审核，不因审核结果自动重画或按评分选图。
- 单图每个目标保留首张完整生成结果；商品长图各段生成后直接拼接。参考素材分析、提示词准备和长图内容规划继续用于创作。
- `delivery.mode=direct`，评分和 `quality` 为 `null`，候选的审核数组为空。`status=succeeded` 表示生成和保存完成，不表示审核通过。
- 保留图片可解码、内容摘要、候选绑定、受控下载、输出数量、长图段落边界和完整性检查。Web 接受直接交付结果，不要求伪造审核记录。
- 旧审核记录、人工接受以及历史结果下载保持兼容；内部显式启用的历史审核回归路径不作为新任务默认。

## 验证

- 新回归测试先复现旧代码仍调用审核：图片 Agent 5 项预期失败、Web 2 项预期失败。
- 图片 Agent 直接交付、管线、保存、恢复、服务 Worker、公开 API、配置路由、schema、CLI 和相关桌面保存回归：**196 passed / 139.92s**。原始输出：`.tmp/image-direct-focused-tests.log`。
- Web 图片适配与长图接收单元测试：**85 passed / 0.43s**。
- 使用同级图片 Agent 的真实管线和公开 DTO，验证 Web 接收与下载的跨服务测试：**13 passed / 10.27s**，包含默认直接交付、历史审核结果和最佳可用历史结果；模型边界受控，无真实模型调用。
- 改动 Python 文件静态检查通过；公开 schema 已更新。
- 扩展全量检查未完成。发现桌面旧用例 `test_request_maps_materials_and_rejects_invalid_combinations` 和通用长图旧用例 `test_legacy_evidence_completion_preserves_real_source_failure[missing_evidence-needs_input-1]` 失败，已在改动前 Git HEAD 的独立副本中复现，未扩大本次修改范围。该次部分全量输出保存在 `.tmp/image-direct-full-tests.log`，不作为全量通过证据。

## 本地生效

重载前只读确认图片服务无排队或运行任务；平台仅有 3 条无活跃租约的历史 `INVESTIGATING` 记录。已重载本项目图片 API、Web API 和平台 Worker，健康检查及 Worker 活跃状态通过，重载工具返回 `DIRECT_DELIVERY_SERVICES_READY`。

未提交真实付费生成探测，未替换既有作品。
