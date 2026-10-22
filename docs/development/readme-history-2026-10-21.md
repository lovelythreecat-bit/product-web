# README 历史运行与接入记录

> 归档日期：2026-10-21。以下保留 README 美化前工作区的完整正文，仅调整相对链接。其中日期、迁移版本、功能状态及验证数字属于各自记录时点，不能当作当前部署说明。当前入口见[项目 README](../../README.md)，后续证据见[验证记录](../verification)。

---

# 电商 AI 创作平台

当前交付账户、积分、会话与任务、受控存储、作品、后台和运行工具代码。2026-10-15 新增文案 textAgent HTTP 协议接线，等待本地服务 Key 与模型配置 ID 后进行真实模型联调；图片 / 视频真实接入及历史独立桥接仍 **DEFERRED_BY_USER**。本仓库不代表完整首版或生产验收通过。

2026-10-15 后台 Agent 配置按用户确认拆为文本、图片、视频，文本模型配置由本项目后端转发管理，图片和视频暂时留空。接入设置、验证和真实鉴权阻塞见[本次记录](../../docs/verification/agent-configs-2026-10-15.md)。

- [本次范围与历史计划关系](../../docs/development-scope-2026-10-13.md)
- [交付与上线待办](../../docs/release-checklist.md)、[AC-01～30 追踪](../../docs/verification/acceptance.csv)
- [需求终稿](../../docs/电商AI创作平台-首版需求终稿-2026-10-09.md)、[产品设计入口](../../docs/product-design.md)、[V2 暖色视觉基准](../../docs/design/high-fidelity-2026-10-11/visual-reference.md)

2026-10-15 服务连接设置已改为 web 数据库配置：在「Agent 配置 → 文本 → 配置服务连接」填写地址和服务 Key；模型配置仍只保存在 textAgent，由 web 后端代理调用。首次部署需配置加密主密钥并执行迁移，见[本次验证与部署说明](../../docs/verification/text-service-connection-2026-10-15.md)。

## 代码入口

| 范围 | 入口 |
| --- | --- |
| Vue 3 / TypeScript / Vite：官网、注册登录、工作台、作品、个人中心、充值说明、用户 / Agent / 价格 / 任务 / 官网 / 审计后台 | [路由](../../frontend/src/router.ts)、[业务页面与共享组件说明](../../frontend/README.md) |
| Python 3.12 / FastAPI / Pydantic / SQLAlchemy / Alembic，MySQL 8.4 为持久事实源、Redis 7.4 Streams 为调度 | [API factory](../../backend/app/main.py)、[后端依赖锁](../../backend/uv.lock) |
| auth / ledger / catalog / conversations / tasks / dispatch / results / investigations / events / storage / works / assist / admin / site / operations | [后端模块](../../backend/app)、[OpenAPI](../../contracts/openapi.json)、[迁移](../../backend/migrations/versions) |
| AgentAdapter、textAgent 同步 HTTP 适配、TEST_ONLY mock；协议与生产政策草稿 | [适配契约](../../backend/app/agents/contracts.py)、[文本适配器](../../backend/app/agents/text.py)、[Agent 协议](../../contracts/agents)、[政策说明](../../contracts/policies/README.md) |
| 开发依赖、staging 配置与运维工具 | [开发 Compose](../../infra/compose.dev.yaml)、[环境示例](../../infra/env.example)、[运行手册](../../infra/runbooks) |

充值仅说明页，不实现支付订单或渠道。官网案例必须有真实授权，mock 成果不可作为公开案例。普通管理员内容权限独立授权，生产批准来源仍关闭。

## 本地启动

需要 Python 3.12、uv、Node >=22.14、pnpm 11.25.0，以及独立 MySQL 8.4 / Redis 7.4。先核对端口 13306、16379、18081、18000、15173；已有服务不重复启动。当前 Windows/WSL 依赖入口与工具路径见[工程说明](../../docs/development/t01-bootstrap.md)，该文档保留 T01 历史；当前迁移 head 为 **0028_media_execution**，测试库以本次环境示例和前端说明的隔离库为准。图片/视频的连接、配置归属、启用限制及验证见[接入记录](../../docs/verification/image-video-integration-2026-10-16.md)。

从仓库根目录安装锁定依赖，启动开发依赖（已有健康实例可复用）：

```powershell
uv sync --frozen --project backend
pnpm --dir frontend install --frozen-lockfile
docker compose -f infra/compose.dev.yaml up
```

Windows/WSL 若需保持活跃会话，可使用工程说明中的前台 WSL Compose 命令。另开终端，首次将 [backend/.env.example](../../backend/.env.example) 复制为 `backend/.env`，按本机环境修改数据库、Redis 和绝对存储路径。API、Alembic 和 Worker 自动读取这份文件，路径固定在 backend 目录，不受当前工作目录影响；环境变量优先于文件。`backend/.env` 和本地存储目录不提交 Git。已有本地配置时不要覆盖。

```powershell
# 首次配置；已有 backend/.env 时跳过复制。
Copy-Item backend/.env.example backend/.env
# 按 .env 中 APP_STORAGE_ROOT 的实际路径创建目录。
New-Item -ItemType Directory -Force -Path 'F:/Work/电商/web/.local-data/storage' | Out-Null
```

APP 数据库为开发库，TEST_DATABASE_URL 仅为隔离测试库，不能互换。[infra/env.example](../../infra/env.example) 保留基础设施和测试配置说明，不要直接复制为后端 `.env`。单元测试和显式构造 `Settings` 的工具不自动读取本地文件。确认 `backend/.env` 中目标为本地开发数据库后执行迁移；迁移仅首次启动或拉取新增迁移后需要：

```powershell
uv run --frozen --project backend alembic -c backend/alembic.ini upgrade head
```

以后日常启动后端只需：

```powershell
uv run --frozen --project backend uvicorn app.main:application --factory --app-dir backend --host 127.0.0.1 --port 18000
```

另一终端：

```powershell
pnpm --dir frontend dev
```

Vite 默认 HTTP 127.0.0.1:15173，将 /api 代理到 127.0.0.1:18000；API_PROXY_TARGET 可改目标，不把秘密放入 VITE_*。live/ready 接口为 /api/v1/health/live 与 /api/v1/health/ready。ready 校验数据库连接、迁移版本与当前代码 head 一致，以及持久目录。未迁移或旧版本数据库返回 503、`checks.database=false`；只启动 MySQL 不代表业务表已准备好。ready 不证明实际备份恢复。

Windows 日常启动直接双击项目根目录的 [启动后端.cmd](../../启动后端.cmd)，一键检查 MySQL、Redis，拉起文案 API、图片 API、视频 API 和视频 Worker、Web API 与平台 Worker。已健康运行的本项目服务直接复用；端口被其他程序占用或已有进程不健康时明确报错，不强杀其他程序。仅当所有服务就绪且平台 Worker 有活跃 Redis 消费者后才显示完整启动成功。启动 Worker 会继续处理数据库中已受理的任务，无需重新提交。

```powershell
# 检查并补齐全部后端服务，持续显示健康检查结果：
.\infra\scripts\restart-api.ps1
# 修改 Web 后端代码后，重启本项目 API 并补齐其他服务：
.\infra\scripts\restart-api.ps1 -RestartApi
# 只预演，不启动、停止任何服务：
.\infra\scripts\restart-api.ps1 -WhatIf
# 启动并检查后返回，不持续监控：
.\infra\scripts\restart-api.ps1 -Check
```

脚本相对仓库定位 `backend/.venv`、`backend/.env` 和同级 `textAgent`、`imageAgent`、`videoAgent` 的各自虚拟环境与配置，默认 Web 端口 18000，可传 `-Port`。模型服务地址、密钥及模型配置仍沿用各自配置，不复制或打印秘密，不自动安装依赖、迁移数据库或发送生成探测。视频进程读取其 `.env`，沿用其中的端口和数据目录。前端 Vite 仍按前端章节单独启动。

持续监控每轮间隔 5 秒，单次检查失败会警告并重试，恢复后继续监控；同一服务连续 3 次检查失败才报错退出，后台服务继续运行。警告、恢复和失败记录保存在 `.local-data/runtime/launcher.log`，各服务日志仍为同目录下的 `<服务名>-*.log`。平台 Worker 的定期核查遇到其他事务占用的用户行锁会留待下轮处理，避免阻塞任务消费。

本机 Web 数据服务按 `backend/.env` 检查；本地 13306/16379 不可达时，只启动已有 `ecommerce-ai-dev-mysql-1` / `ecommerce-ai-dev-redis-1` 容器（支持 Docker Desktop 和 WSL `Ubuntu-24.04`），核验 Compose 项目标签，不创建新容器或数据卷。Agent 配置指向本地 3306 且不可达时尝试启动已有 Windows `MySQL57` 服务；需要的服务管理权限不足时明确失败。已有数据服务的首次安装、配置与迁移仍需先完成。

平台 Worker 默认并发 4，可用 `-Concurrency` 修改。默认复用 Redis 中属于 `local-generation-workers` 的唯一现有 Stream；首次启动使用稳定名称 `local:ecommerce-ai-dev:generation`。存在多个匹配流时要求显式 `-Stream`，也可用 `-Group` 指定消费组，避免每日更换队列。已有 Worker 的并发设置保持不变。

本次拉起的后台进程日志保存在忽略目录 `.local-data/runtime/`，每次启动生成独立文件；复用的服务沿用原日志。启动窗口持续检查服务健康，异常退出会指出具体服务；Ctrl+C 仅停止监控，后台服务和在途任务继续运行。再次双击会复用已有健康进程并补齐缺项。

**裸启动不足以完整登录和演示生成。** 身份 cookie 为 Secure，写操作校验允许的 Origin 和 CSRF；需正确 HTTPS 同源代理与 APP_AUTH_ORIGINS。不得降低这些检查。空库未配置策略版本、目录规格、注册赠送、存储或生成估算时，相关功能保持关闭；启动 mock 服务也不会自动发布这些配置。现有 [HTTPS TEST_ONLY harness](../../frontend/README.md#真实浏览器-harness) 使用隔离库、独立持久目录及测试专属 seed 准备配置与账号，是历史专项验证入口，不是生产启动器；下述本机排障使用已有 Vite 与本地开发 API，不属于重跑该 harness。

2026-10-13 本机运行排障：`ecommerce_ai_dev` 从 `0001_bootstrap` 升级至 `0021_site_content`，修复公开介绍和案例查询的缺表 500。本机忽略的 `backend/.env` 显式允许 `http://127.0.0.1:15173`、`http://localhost:15173`；开发库显式建立 mock / TEST_ONLY 注册策略和 1000 测试积分配置。该配置不会由 API 启动自动创建，也不改变生产政策。在本机 Chrome 的 loopback 地址实测注册、刷新恢复会话、退出和重新登录；Secure cookie 与 Origin / CSRF 检查保留。其他主机或部署地址仍须 HTTPS 和精确 Origin 白名单，测试积分不代表生产赠送额度。

## 文案 textAgent 对接

适配 `ecommerce_copy_api` 1.0，当前服务文档为 <http://127.0.0.1:8000/docs>。平台后端发送 Bearer 服务 Key 和稳定的 `Idempotency-Key`，调用 `POST /v1/copy/generate`；后续只通过 `GET /v1/call-records/{record_id}` 查询和恢复原文案。页面继续使用现有生成、费用确认、任务、作品与下载流程。上游没有流式接口，界面等待完整结果，不生成模拟片段。

当前通过后台「Agent 配置 → 文本」保存服务连接、管理远端模型，并在模型列表中明确设置一个默认模型。数据库迁移至 `0025_text_default_model`，配置一次持久的 `APP_TEXT_SERVICE_ENCRYPTION_KEY`。服务 Key 由 textAgent 签发，需要 `configs:read`、`configs:write`、`generate` 和 `records:read`；模型厂商 Key 仅写入 textAgent 的模型配置，不在 web 保存副本。

「文本服务接入」列表、编辑表单和独立 profile 配置流程已删除。设置默认模型后，服务端自动维护内部「文本创作」能力，用于规格、报价和历史任务关联。新的文本任务不读取 `APP_TEXT_AGENT_PROFILES`；该字段只兼容已有旧任务。服务连接修改后立即用于后续管理及生成请求，无需重启 API/Worker。

受理时固定非秘密的原服务地址、模型 UUID 和图片能力；切换默认模型不会改变已提交任务。Worker 使用当前数据库连接访问原服务、原模型和原记录；服务 origin 改变后拒绝错误路由，不把旧任务转交新服务。更换 origin 会清除默认模型选择。服务 Key、模型 Key 和密文不进入任务快照或日志。

平台文本协议与输入契约由代码维护，切换模型能力不会使已有规格失效；具体图片能力在受理前校验。规格、积分价格、生成开放、容量与恢复政策继续使用既有 CatalogService / PolicyService，不因模型配置成功而自动启用或产生真实费用：

- 输入：商品名称必填；文本服务接受最多 4 张静态 JPEG/PNG/WebP，每张不超过 10 MiB；含图片的请求在受理前校验当前默认模型是否支持图片，平台仅发送原任务拥有且校验通过的素材字节。
- 规格：只支持单份完整文案。现有语气直接传入；数字长度映射到 `max_chars`，文字长度档位保留为明确的长度指令，不擅自赋予字数。未知参数或多份规格在受理前拒绝。
- D-01：`agents` 节绑定 `text-agent-v1`；`result_specs[spec_id]` 固定该规格的 `spec_version`、规范化 `SpecVersion` 的 `spec_digest`、`protocol_version=text-agent-v1`、`expected_item_keys=["original-1"]`、`media_type=text/plain`。D-03、D-02、D-05 分别绑定实际输入、规格和既有确认费用，不能将测试费用当生产报价。
- D-10：完整保留原生成容量政策；`generation.allowed_download_sources` 和 `result_download.allowed_download_sources` 允许 `text-agent-v1:bound-record`。这是受控查单读取标记，不授权任意 URL。保留其他仍使用的来源及各自限额。新规格还需在 `APP_GENERATION_CAPACITY_ESTIMATES` 中登记实际估算；`APP_GENERATION_POLICY_VERSIONS` 应包含对应内部文本 Agent 与规格的实际生成政策记录；设置默认模型不会替代这些生成开放与结果恢复规则。

完整正文持久保存、作品及最终消息发布完成后才按原固定费用结算；HTTP 错误本身不授权扣费或释放。同步生成等待期间续租 Worker 租约。已知记录 ID 时查询原记录；响应格式异常也保留已知 ID。上游暂不提供按幂等键查单：若提交响应完全丢失且无记录 ID，任务进入待核查并保留冻结，不自动重新 POST。有限的幂等保留期不能作为永久安全重试依据。模型中断、记录过期和保存失败均不触发新生成；确定失败记录才进入现有释放流程。

新增迁移 `0023_text_agent_routing` 仅添加可空的非秘密路由快照，已有任务不回填、不改写。部署前按本地启动章节迁移数据库。该段为早期验证边界。2026-10-15 后续已通过后台保存服务连接及 abc 模型，并设置为工作台默认；当前真实生成仍未调用，详见[统一配置验证](../../docs/verification/unified-text-generation-2026-10-15.md)。

## 验证边界

2026-10-15 文本接线验证：实际读取本机 textAgent OpenAPI，与源服务 DTO 核对；新增文本适配单元、平台 HTTP 受理及受控 HTTP / MySQL / Redis / 硬盘 / 积分集成检查。连同受影响的原任务受理、回调、结算、上游核查与保存恢复回归，共 **364 passed / 280.42s，0 failed、0 skipped**，限定文件 Ruff 通过。覆盖同步正文保存后结算一次、确定失败释放一次、无记录 ID 的断连不重新生成、保存失败恢复原成果、长调用续租约、缺凭据与非法字段不冻结、受理时固定模型配置；限定代码评审发现的四处恢复 / 校验问题已修复并复核。最终日志为 `.local-data/text-agent-verification-final-2026-10-15.log`。本机开发库 `ecommerce_ai_dev` 已升级到 `0023_text_agent_routing`，实查新增字段存在。以上使用受控文本 HTTP 服务，没有真实模型调用、真实目录启用、前端全量浏览器验证或生产政策确认。

2026-10-13 本机排障验证：先复现实际首页接口 500、注册 403 和旧库错误返回 ready；新增迁移回归先出现 3 个预期失败，修复后通过。完整后端初跑为 612 passed / 9 failed，进一步修复 HTTP 日志中间件多预取一个下载块的问题，以及容量并发测试误设共享测试库为空的前提。保留原撤权后最多一个已授权缓冲块、并发容量恰有一个请求成功的断言。针对性 70 项通过后，同一隔离 MySQL / Redis 环境完整重跑 **621 passed / 864.11s，0 failed、0 skipped**；全后端 Ruff 与 OpenAPI 检查通过。独立只读复核未发现新增问题。本机原始日志分别为 `.local-data/backend-verification-2026-10-13.log`、`.local-data/backend-regressions-2026-10-13.log` 和 `.local-data/backend-verification-final-2026-10-13.log`，保留失败证据，不用后续通过结果覆盖它。

实际 Chrome 经 Vite 代理验证首页两接口 200、注册 201、刷新后本人资料 200、账户 200、退出 204、重新登录 200；未登录本人资料 401 属于正常行为。上述仅覆盖本地 mock / TEST_ONLY 运行和本次后端测试，未执行全量前端浏览器矩阵，也不代表生产政策、真实 Agent 或部署验收。

历史正式专项记录在 [docs/verification](../../docs/verification)，每份记录说明其真实检查、证据及未验范围。T18～T25 原聚合仍待完成；全量双端 / 故障矩阵、真实 Agent、实际部署与备份恢复、D-01～D-12 生产确认没有被本次文档交付替代。
