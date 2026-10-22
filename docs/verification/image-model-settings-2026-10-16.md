# 图片 Agent 两类模型配置验证

日期：2026-10-16。范围：用户要求将后台图片配置收敛为文字模型和图片生成模型；未调用真实供应商，未执行生成、生产迁移或部署。

## 实现与交互

- 图片页保留 imageAgent 服务连接，只展示文字模型、图片生成模型的摘要与「配置模型」入口；编辑使用原 AppDrawer、Element Plus 公共控件和 V2 暖色主题。
- 两类模型分别填写 API 地址、模型名称与只写 Key；文字模型固定 Chat Completions 并提示须支持图片输入，生图支持 OpenAI Images / OpenRouter Images。首次配置、更换地址/协议须填 Key，原配置留空保留。
- 新增 GET/PATCH `/api/v1/admin/media-agents/image/models`；管理员权限、CSRF、审计、连接 revision 和当前模型/服务/方案 version 检查继续生效。
- 后端读取当前方案映射；保存先创建所需新服务/模型和完整方案，再版本化切换连接。原模型/服务/方案不原地修改，历史任务仍可读取旧连接。新方案使用 `vision` 和 `fast` 内部绑定，其他文字阶段回退到同一 vision，保留原运行参数。
- 上游失败不激活半套配置。已创建但尚未被引用的上游资源可能保留，不自动删除；不声称多个上游 HTTP 写入是一个跨服务事务。
- 打开自动读取最新配置；失败保留输入；409 阻止重提，关闭再打开重读；关闭清空 Key。异步打开期间保留触发按钮焦点，禁止重复动作，关闭后恢复焦点。
- 视频和独立文本模型流程保持原约定。旧图片资源代理接口留作兼容，不再作为图片页面操作入口。

## 代码与接口验证

- 后端：`test_image_model_settings.py`、`test_media_config.py`、`test_image_agent.py`、`test_media_execution.py` 共 **82 passed**。覆盖两模型自动绑定、密钥留空复用、保留自定义路径/参数、旧图不变、各阶段失败不激活、并发连接与资源冲突、身份错误、协议/空字段校验及权限/CSRF/审计。
- 前端：`image-agent-configs.spec.ts`、`media-agent-configs.spec.ts`、`media-workspace.spec.ts` 共 **23 passed**。覆盖最新读取、两类字段、空 Key、取消清理、协议变化须 Key、冲突草稿保留及现有视频配置。
- TypeScript 类型检查、Vite 生产构建、相关 Python Ruff 检查、OpenAPI 与生成 TypeScript 契约一致性检查通过。
- 使用当前项目环境：pnpm 系统 shim 不可用，直接以 Node 调用已安装工具；Vitest TEMP 指向项目 `.local-data/test-tmp`。沙箱内 Edge 启动失败后，经工具审批在沙箱外运行无头 Edge；所有接口由测试拦截。
- 独立只读代码评审未发现需要修复的问题；不将其视为真实供应商联调。

## 浏览器与视觉验证

`playwright.media.config.ts`：桌面 1440×1000、手机 390×844，共 **10 passed**。包含本轮两模型表单保存、回显、协议选择、Key 清空、冲突恢复、打开/关闭焦点、无整页横向溢出，以及既有文本/视频媒体交互回归。测试合成数据曾因旧模型列表响应形状与新按钮断言不匹配失败，已修正后重跑；新协议选择的可访问名称和异步打开的焦点问题也已修复并通过真实浏览器复核。

人工查看下列截图：暖色摘要层级清楚，两类模型在同一抽屉内分组，手机单列、内容区滚动、底部操作固定。图中全部模型和 Key 均为 TEST_ONLY 合成资料。

- [桌面摘要](screenshots/image-model-settings-2026-10-16-summary-desktop.png)
- [桌面抽屉](screenshots/image-model-settings-2026-10-16-drawer-desktop.png)
- [手机摘要](screenshots/image-model-settings-2026-10-16-summary-mobile.png)
- [手机抽屉](screenshots/image-model-settings-2026-10-16-drawer-mobile.png)

真实文字模型是否支持图片输入、供应商权限及出图效果仍须使用实际配置联调；本次未执行收费调用，不改变原有计费或生产启用门槛。
