# Agent 三类配置调整与验证

日期：2026-10-15。依据：用户确认将 Agent 配置拆分为文本、图片、视频；文本通过本项目后端对接 `http://127.0.0.1:8000` 的模型配置 API，图片和视频暂时留空。

## 实现

- 后台 Agent 页使用文本、图片、视频三个分类入口，默认展示文本；图片、视频只展示空状态，不提供新增、编辑或预填模型。
- 文本模型支持分页查询、新增、编辑、密钥轮换与启停；编辑使用既有抽屉组件，修改原因写入平台审计。原有文本 Agent 版本与输入能力配置继续保留；规格和价格页不改变流程。
- 平台后端提供 `/api/v1/admin/text-model-configs` 的 GET / POST，以及 `/{config_id}` 的 GET / PATCH；后端持有服务访问 Key，并转发至 `/v1/model-configs`。前端请求只使用平台同源路径，不请求 8000 端口。
- 修改携带原 revision，由后端转为 `If-Match: "revision"`。冲突返回 409，保留草稿并禁用继续保存；管理员明确放弃草稿后，按配置 ID 读取最新版本再编辑，避免分页导致找不到当前配置。
- 编辑时密钥留空即不发送 `api_key`；新密钥为写入字段。上游响应按字段投影，意外携带的密钥字段被丢弃；上游原始错误不回传。平台审计仅记录配置 ID、revision、操作人和修改原因，不记录模型密钥、服务密钥或完整配置。
- 查询及写入重新检查管理员身份；写入保留 CSRF 检查。禁止服务重定向，不自动重试配置写入。

## 后端连接设置（本轮更新）

本轮用户确认：服务连接存入 web 数据库，模型配置仍仅存 textAgent。原 `APP_TEXT_MODEL_SERVICE` 管理配置方式已被替代；管理接口不再从环境或生成 profile 回退。详见[服务连接入库验证与部署](text-service-connection-2026-10-15.md)。

后台「Agent 配置 → 文本 → 配置服务连接」保存地址和服务 Key；Key 加密入库且不回传。服务 Key 必须由 textAgent 授予 `configs:read` / `configs:write`，与模型 API Key 不同。首次部署配置独立的 `APP_TEXT_SERVICE_ENCRYPTION_KEY`、执行迁移并重启 API；以后保存连接无需重启。

新增模型不会自动切换生成任务模型。现有生成 profile、模型绑定与目录/政策流程保持原状，不由本次管理连接配置自动发布。

## 验证

- 后端定向检查：`test_text_model_configs.py`、`test_text_agent.py`、`test_runtime_config.py` 共 46 项通过。覆盖服务端鉴权、密钥不回传、revision 转发、上游错误脱敏、配置校验、管理员与 CSRF 拒绝、既有文本调用兼容。
- 前端定向单测：`text-model-configs.spec.ts`、`admin-remediation.spec.ts`、`admin-state.spec.ts` 共 17 项通过。覆盖编辑、密钥留空、版本冲突与重新加载、分页、图片和视频空配置及规格页兼容。
- 前端类型检查、Vite 构建、OpenAPI 导出一致性、TypeScript 契约一致性及本次后端 Ruff 检查通过。
- 浏览器桌面 1440×1000、手机 390×844 共 2 项通过，使用独立 TEST_ONLY 夹具与模拟列表，验证分类切换、整页无横向溢出、抽屉初始焦点及 Escape 关闭恢复焦点；此类验证不证明真实鉴权或模型生成成功。[桌面截图](screenshots/agent-configs-2026-10-15-desktop.png)、[手机截图](screenshots/agent-configs-2026-10-15-mobile.png)为真实组件渲染与模拟数据，不包含主应用导航壳。表格在自身容器横向滚动。

## 真实联调阻塞（此前检查记录，本轮未签发新 Key）

已按用户授权检查 `F:/Work/电商/textAgent` 的本地配置。`.cache/api-browser-session.json` 中保存的旧服务 Token 对当前 8000 服务返回 401；只读检查 `api-config.local.json` 指向的开发数据库，当前接入方和模型配置均为空。

创建接入方及签发新 Key 的请求被自动审批拒绝，理由是用户仅授权取用已有配置，尚未明确授权建立身份或授予作用域。操作没有执行；没有创建接入方、签发密钥、修改真实模型配置或触发模型生成。后续需要用户明确授权创建接入方并签发配置读写作用域 Key，或提供可用的既有服务 Key。当前 API / Worker 的真实生成配置仍未启用。
