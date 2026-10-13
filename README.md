# 电商 AI 创作平台

当前交付账户、积分、会话与任务、受控存储、作品、后台和运行工具代码。三核心文案 / 图片 / 视频 Agent 仍在调试，本次只保留平台适配与 TEST_ONLY mock 入口，真实接入和独立桥接均 **DEFERRED_BY_USER**。本仓库不代表完整首版或生产验收通过。

- [本次范围与历史计划关系](docs/development-scope-2026-10-13.md)
- [交付与上线待办](docs/release-checklist.md)、[AC-01～30 追踪](docs/verification/acceptance.csv)
- [需求终稿](docs/电商AI创作平台-首版需求终稿-2026-10-09.md)、[产品设计入口](docs/product-design.md)、[V2 暖色视觉基准](docs/design/high-fidelity-2026-10-11/visual-reference.md)

## 代码入口

| 范围 | 入口 |
| --- | --- |
| Vue 3 / TypeScript / Vite：官网、注册登录、工作台、作品、个人中心、充值说明、用户 / Agent / 价格 / 任务 / 官网 / 审计后台 | [路由](frontend/src/router.ts)、[业务页面与共享组件说明](frontend/README.md) |
| Python 3.12 / FastAPI / Pydantic / SQLAlchemy / Alembic，MySQL 8.4 为持久事实源、Redis 7.4 Streams 为调度 | [API factory](backend/app/main.py)、[后端依赖锁](backend/uv.lock) |
| auth / ledger / catalog / conversations / tasks / dispatch / results / investigations / events / storage / works / assist / admin / site / operations | [后端模块](backend/app)、[OpenAPI](contracts/openapi.json)、[迁移](backend/migrations/versions) |
| AgentAdapter、TEST_ONLY mock；协议与生产政策草稿 | [适配契约](backend/app/agents/contracts.py)、[Agent 协议](contracts/agents)、[政策说明](contracts/policies/README.md) |
| 开发依赖、staging 配置与运维工具 | [开发 Compose](infra/compose.dev.yaml)、[环境示例](infra/env.example)、[运行手册](infra/runbooks) |

充值仅说明页，不实现支付订单或渠道。官网案例必须有真实授权，mock 成果不可作为公开案例。普通管理员内容权限独立授权，生产批准来源仍关闭。

## 本地启动

需要 Python 3.12、uv、Node >=22.14、pnpm 11.25.0，以及独立 MySQL 8.4 / Redis 7.4。先核对端口 13306、16379、18081、18000、15173；已有服务不重复启动。当前 Windows/WSL 依赖入口与工具路径见[工程说明](docs/development/t01-bootstrap.md)，该文档保留 T01 历史；当前迁移 head 为 **0021_site_content**，测试库以本次环境示例和前端说明的隔离库为准。

从仓库根目录安装锁定依赖，启动开发依赖（已有健康实例可复用）：

```powershell
uv sync --frozen --project backend
pnpm --dir frontend install --frozen-lockfile
docker compose -f infra/compose.dev.yaml up
```

Windows/WSL 若需保持活跃会话，可使用工程说明中的前台 WSL Compose 命令。另开终端，按 [infra/env.example](infra/env.example) 设置 APP_MODE、APP_TEST_ONLY、APP_DATABASE_URL、APP_REDIS_URL；示例文件不会自动加载。APP 数据库为开发库，TEST_DATABASE_URL 仅为隔离测试库，不能互换。另须准备已存在、可写的绝对持久目录并设置 APP_STORAGE_ROOT 与 APP_STORAGE_PERSISTENT=true。确认目标为本地开发数据库后执行：

```powershell
uv run --frozen --project backend alembic -c backend/alembic.ini upgrade head
uv run --frozen --project backend uvicorn app.main:application --factory --app-dir backend --host 127.0.0.1 --port 18000
```

另一终端：

```powershell
pnpm --dir frontend dev
```

Vite 默认 HTTP 127.0.0.1:15173，将 /api 代理到 127.0.0.1:18000；API_PROXY_TARGET 可改目标，不把秘密放入 VITE_*。live/ready 接口为 /api/v1/health/live 与 /api/v1/health/ready。ready 校验数据库和持久目录，不证明实际备份恢复。

**裸启动不足以完整登录和演示生成。** 身份 cookie 为 Secure，写操作校验允许的 Origin 和 CSRF；需正确 HTTPS 同源代理与 APP_AUTH_ORIGINS。不得降低这些检查。空库未配置策略版本、目录规格、注册赠送、存储或生成估算时，相关功能保持关闭；启动 mock 服务也不会自动发布这些配置。现有 [HTTPS TEST_ONLY harness](frontend/README.md#真实浏览器-harness) 使用隔离库、独立持久目录及测试专属 seed 准备配置与账号，是历史专项验证入口，不是生产启动器。本次未安装依赖、启动服务或重跑该 harness。

## 验证边界

历史正式专项记录在 [docs/verification](docs/verification)，每份记录说明其真实检查、证据及未验范围。T18～T25 原聚合仍待完成；全量双端 / 故障矩阵、真实 Agent、实际部署与备份恢复、D-01～D-12 生产确认没有被本次文档交付替代。
