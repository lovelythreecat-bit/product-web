# 文本服务连接入库验证

日期：2026-10-15。依据：用户确认服务连接只存 web 数据库，模型配置只由 textAgent 保存，撤回模型配置双写方案。

## 结果与数据归属

- web 新增 `text_service_connections` 单例表，保存服务地址、加密服务访问 Key、revision、修改人及时间。没有新增本地模型配置表，也不保存模型 API Key。
- 后台「Agent 配置 → 文本 → 配置服务连接」使用已有暖色抽屉；首次及变更地址要求填写服务 Key，原地址编辑留空保留旧 Key。GET 只返回 Key 是否已配置。
- 新增 GET / PATCH `/api/v1/admin/text-service-connection`；查询和写入重新检查管理员身份，写入保留 CSRF 检查。单例行锁和 expected_revision 防止并发覆盖，配置与审计同事务提交。
- Key 使用 Fernet 认证加密，密文绑定用途和服务 origin。主密钥只放后端环境。读取模型配置时逐次加载数据库连接，更新后立即生效；解密失败不回退到环境 Key 或生成 profile。
- 模型 GET / POST / PATCH 仍转发至 textAgent `/v1/model-configs`。模型参数及模型 Key 由 textAgent 持有；web 只保留配置 ID/revision 等审计元数据。远端配置写入无自动重试。
- 本次不自动修改生成 profile、任务模型绑定、既有快照、规格、积分价格、图片或视频接入。

## 首次部署

1. 在后端环境设置一次持久的 `APP_TEXT_SERVICE_ENCRYPTION_KEY`，使用 `cryptography.fernet.Fernet.generate_key()` 生成。真实值不提交仓库；需在备份恢复时保留原主密钥，与数据库备份分开保管。不要在每次启动时生成新值。
2. 核对目标库后执行 `alembic -c backend/alembic.ini upgrade head`，新增迁移为 `0024_text_service_connection`。迁移只创建连接表及未配置的单例行，不写入服务 Key 或模型配置。
3. 部署新增代码及加密环境后重启 API 一次。以后在后台保存地址或 Key 无需重启。
4. 管理员在页面填写 textAgent 的 origin 及具有 `configs:read` / `configs:write` 的服务访问 Key。该 Key 与模型厂商 Key 不同。连接保存成功只证明本地配置已保存，上游权限仍通过模型接口响应确认。

旧 `APP_TEXT_MODEL_SERVICE` 字段只为升级时兼容环境解析而保留，已不作为模型管理的读取来源。已有生成 profile 不受此管理连接改动影响。

## 本机执行

- 已只读核对本地开发库为 `127.0.0.1:13306/ecommerce_ai_dev` 后执行新增迁移；数据库当前为 `0024_text_service_connection`。
- 已在忽略提交的 `backend/.env` 初始化一次持久加密主密钥，没有输出真实值，没有填写或签发服务访问 Key。
- 核实 18000 端口进程确属本项目 API 后重启。真实 `/api/v1/health/ready` 返回 200，存储及数据库检查均为 true；未登录读取新增配置接口返回 401。
- 当前本机连接行仍未配置服务地址/Key；需要管理员在新入口填写可用凭据。没有修改真实 textAgent 模型配置或调用真实模型生成。

## 最终验证证据

| 检查 | 最终结果与范围 |
| --- | --- |
| 后端定向单测与集成检查 | **58 passed / 7.17s**，包含 54 项单测及 4 项真实隔离 MySQL + 受控 HTTP 检查 |
| 前端定向单测 | **15 passed**：服务连接、原文本模型配置、后台兼容 |
| 浏览器桌面与手机 | **4 passed / 11.1s**，Chrome 独立会话、1440×1000 与 390×844，现有 Vite + TEST_ONLY 模拟接口 |
| 前端类型检查与生产构建 | 通过；vue-tsc、Vite 构建 |
| Ruff、OpenAPI 与 TypeScript 契约 | 本次限定后端文件检查及生成产物一致性检查通过 |
| 代码复核 | 独立只读复核未发现本次新增功能的可操作问题；指出的旧双写设计文档已替换 |

后端实际覆盖连接落库与重新读取、密钥密文/只写、留空保留、地址更换、revision 冲突、管理员/CSRF 拒绝、损坏密文拒绝、错误主密钥拒绝，以及轮换后下一个真实 HTTP 请求使用新 Key。模型新增和 PATCH 实际发送给受控 HTTP 服务并核对请求与 If-Match；web 库中不落模型 Key。

浏览器实际覆盖分类兼容、初始焦点、保存后重新查询远端模型、编辑不回填 Key、留空不发送 Key、Escape 关闭恢复焦点及无整页横向溢出。截图为真实组件配合 TEST_ONLY 模拟数据，不证明真实 textAgent 凭据或生成能力可用：

- [桌面页面](screenshots/service-connection-2026-10-15-desktop.png)、[桌面抽屉](screenshots/service-connection-drawer-2026-10-15-desktop.png)。
- [手机页面](screenshots/service-connection-2026-10-15-mobile.png)、[手机抽屉](screenshots/service-connection-drawer-2026-10-15-mobile.png)。

后端最终日志为 `.local-data/service-connection-backend-final-2026-10-15.log`，前端最终日志为 `.local-data/service-connection-frontend-final-2026-10-15.log`。集成检查使用既有隔离库 `ecommerce_ai_test_t07_20261011`，没有清理历史测试记录。已检查本次跟踪及未跟踪源文件空白；仓库其他既有页面的尾部空行不在本次修改范围。

本记录不代表前后端全量回归、真实上游鉴权/模型调用、完整生成流程或生产验收。
