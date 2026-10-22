# T01 工程基础与启动说明

本步建立可启动工程、共享 DTO、测试设施与开发容器。仅提供 `/api/v1/health/live`、`/api/v1/health/ready` 和明确标识 TEST_ONLY 的前端启动页；没有实现业务页面、生成、积分或生产政策。生产能力仍受后续 D-01～D-12 门槛约束。

## 锁定工具链

- Python 3.12（本机与容器实测 3.12.14），uv 0.12.19；依赖由 `backend/pyproject.toml` 与 `backend/uv.lock` 精确锁定。
- FastAPI 0.143.0、Pydantic 2.14.0、SQLAlchemy 2.1.4、Alembic 1.20.0。SQLAlchemy 使用同步 Session；模块服务共享事务，不自行提前 commit。
- Node 22.14.0、pnpm 11.25.0、Vue 3.5.43、TypeScript 5.9.3、Vite 7.3.7、Vitest 4.1.11、Playwright 1.64.0；依赖见 `frontend/pnpm-lock.yaml`。pnpm 工作区仅允许 esbuild 构建脚本。
- Compose 固定项目名 `ecommerce-ai-dev`；MySQL 8.4.8、Redis 7.4.8、Python 3.12.14 均锁定镜像摘要。Redis 使用 Docker Official Images 的公开 ECR 副本，同版本 Docker Hub blob 在本机多次下载超时。

Redis Streams 为后续薄调度器选择，暂不引入 Celery。MySQL 始终是任务、账本和恢复事实来源；T07/T08 才实现事务 Outbox、租约和扫描恢复。Redis 测试只证明 Streams 连接往返，不代表调度恢复已实现。

## Windows + WSL 开发入口

以下命令从项目根目录运行。当前默认 pnpm 路径失效，使用下列已核验路径；其它机器可用自己的同版本 uv/pnpm。

```powershell
$uvT01 = 'C:/Users/呜啦啦/.local/bin/uv.exe'
$pnpmT01 = 'C:/Users/呜啦啦/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback/pnpm.cmd'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:UV_LINK_MODE = 'copy'
& $uvT01 sync --frozen --project backend
& $pnpmT01 --dir frontend install --frozen-lockfile
```

开发服务占用 **13306 / 16379 / 18081**；API 使用 **18000**，Vite 使用 **15173**。先检查端口没有其它服务。端口默认仅绑定回环，MySQL/Redis 数据存于本项目独立卷，不复用本机 MySQL 5.7 或 Redis 5。

在一个持续打开的终端运行：

```powershell
wsl.exe -d Ubuntu-24.04 -- docker compose -f /mnt/f/Work/电商/web/infra/compose.dev.yaml up
```

让该命令保持前台运行，等三个服务 healthy 后再运行测试/API。本机观察到 WSL 空闲后容器接收 shutdown；单独 `up -d` 后关闭所有 WSL 会话不能保证服务继续存在。保持活跃 WSL 后，Windows `127.0.0.1:13306` 已实测可连接。不要因连接被拒绝直接判断为转发故障，先核对容器状态。

另一终端可用有界健康等待：

```powershell
wsl.exe -d Ubuntu-24.04 -- timeout 45 docker compose -f /mnt/f/Work/电商/web/infra/compose.dev.yaml up -d --wait --wait-timeout 30
```

如果其它机器上容器 healthy 且保持 WSL 活跃，但 localhost 仍不可达，可读 `wsl.exe -d Ubuntu-24.04 -- hostname -I`，选择当前 WSL 私网地址，通过 `wsl.exe -d Ubuntu-24.04 -- env DEV_BIND_ADDRESS=<该地址> docker compose -f ... up` 仅绑定该地址；数据库/Redis URL 同步改用它。本机私网路径也已实际连接验证。地址可能随 WSL 重启变化，不写死到源码，不修改系统转发或全局 Docker 配置。

## API 与前端

2026-10-13 更新：API、Alembic 与 Worker 自动读取 `backend/.env`，环境变量优先于文件。首次从 `backend/.env.example` 复制并按本机环境修改，之后无需重复设置下方环境变量；最新启动步骤见仓库 README。`infra/env.example` 仍是基础设施与测试配置说明，不会自动加载。以下保留 T01 环境变量启动方式作为历史参考。开发凭据的 `TEST_ONLY` 是明确的公开测试值。

```powershell
$env:APP_MODE = 'mock'
$env:APP_TEST_ONLY = 'true'
$env:APP_DATABASE_URL = 'mysql+pymysql://ecommerce_dev:TEST_ONLY_dev_local@127.0.0.1:13306/ecommerce_ai_dev?charset=utf8mb4'
$env:APP_REDIS_URL = 'redis://127.0.0.1:16379/0'
$env:APP_STORAGE_ROOT = Join-Path (Get-Location) 'backend/.local-data/storage'
New-Item -ItemType Directory -Force -Path $env:APP_STORAGE_ROOT | Out-Null
$env:APP_STORAGE_PERSISTENT = 'true'
& $uvT01 run --frozen --project backend alembic -c backend/alembic.ini upgrade head
& $uvT01 run --frozen --project backend uvicorn app.main:application --factory --app-dir backend --host 127.0.0.1 --port 18000
```

在另一终端启动前端：

```powershell
& $pnpmT01 --dir frontend dev
```

打开 `http://127.0.0.1:15173`。Vite 将 `/api` 代理到 `http://127.0.0.1:18000`；可通过非公开的 `API_PROXY_TARGET` 环境变量改变代理目标。不要把凭据放入 `VITE_*`。

- `GET http://127.0.0.1:18000/api/v1/health/live` 返回 200 及 `mode`、`test_only`。
- ready 要求数据库 `SELECT 1` 成功、实际 Alembic revision 与当前代码 migration head 一致，并且显式声明 `APP_STORAGE_PERSISTENT=true`，持久根为已存在的绝对目录，可写入/flush/fsync。任何条件不满足返回 503、`ready=false` 和安全的布尔检查结果，不返回内部路径或连接信息，也不自动创建存储根。2026-10-13 补充迁移检查：未初始化、旧版本或未知版本数据库不能仅凭连接成功返回 ready；先执行 `alembic upgrade head`，再启动业务接口。
- 该检查验证配置声明与可写性，不能代替 T24 对实际磁盘挂载、备份恢复和断电持久性的验收。
- staging/production 拒绝 `test_only=true`，也拒绝数据库/Redis URL、存储路径里的 TEST_ONLY 标记。设置 `APP_TEST_ONLY=false` 不等于业务生产门槛已确认。
- Redis 不参与 readiness 判定；其故障不应把持久任务解释为不存在。

## 测试与数据库隔离

```powershell
$env:APP_MODE = 'mock'
$env:TEST_ONLY = 'true'
$env:TEST_DATABASE_URL = 'mysql+pymysql://ecommerce_test:TEST_ONLY_test_local@127.0.0.1:13306/ecommerce_ai_test?charset=utf8mb4'
$env:TEST_REDIS_URL = 'redis://127.0.0.1:16379/15'
& $uvT01 run --frozen --project backend pytest backend/tests -q
& $uvT01 run --frozen --project backend ruff check backend
& $pnpmT01 --dir frontend typecheck
& $pnpmT01 --dir frontend build
& $pnpmT01 --dir frontend test
```

共享 `backend/tests/conftest.py` 在执行任何 SQL 前要求 `TEST_ONLY=true`、`APP_MODE=mock`、驱动 mysql+pymysql、数据库固定 ecommerce_ai_test、用户固定 ecommerce_test。初始化脚本仅授予该用户测试库权限；fixture 不接受开发库或 SQLite。没有测试连接变量时明确 skip，连接失败/错误版本则报错，skip 不算集成通过。

`backend/tests/unit/conftest.py` 仅在每个单元测试开始前清除继承的 `APP_*`，测试仍可通过 `monkeypatch.setenv` 显式验证环境配置；结束后恢复调用者环境，不影响集成测试的 `APP_MODE`、`TEST_DATABASE_URL` 或 `TEST_REDIS_URL`。

session 级 fixture 在 MySQL 命名锁保护下执行 Alembic `upgrade head`。T01 只有空的 `0001_bootstrap` 基线，不提前建业务表。每个 `db_session` 使用外部事务加 savepoint，即使应用 commit 也不会泄漏到其它连接，结束后 rollback。T01 探针表按 UUID 单独建表、最终仅 drop 自己的表；MySQL DDL 隐式提交，所以不放在回滚事务中。后续模块扩展 Alembic 迁移和真实约束测试。Redis 仅允许数据库 15，测试只清理自己的随机 key 前缀，禁止 FLUSHALL/全库 reset。

T02 追加：政策历史由数据库触发器保护。开发 Compose 的 MySQL 实例显式启用 `log_bin_trust_function_creators=ON`，允许仅有本库 schema 权限的迁移用户创建触发器；没有给应用或测试用户授予 SUPER。开启 binary logging 的其他部署环境须提前安排该实例配置或有资格的独立迁移账户，再执行迁移。MySQL DDL 失败不自动回滚；只可在核验表为空、revision 及对象归属后按失败迁移记录处理，不自动删表或清库。

Linux 一致测试入口（与 Windows 共用源码、uv.lock）：

```powershell
wsl.exe -d Ubuntu-24.04 -- timeout 240 docker compose -f /mnt/f/Work/电商/web/infra/compose.dev.yaml run --rm backend-test -q
```

runner 使用只读源码绑定与项目独立 `test_runtime` 卷，首次安装 uv 0.12.19 并按 frozen lock 安装依赖；直连 Compose 网络中的 mysql/redis，不依赖 Windows 端口转发。首次网络下载失败属于环境失败，应保留输出并重试，不能计为行为 RED。

浏览器测试仅覆盖当前启动页，不要求未来业务页存在：

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) 'frontend/.cache/ms-playwright'
& $pnpmT01 --dir frontend exec playwright install chromium --only-shell
& $pnpmT01 --dir frontend test:e2e
```

也可设置 `PLAYWRIGHT_CHANNEL=msedge` 使用已安装 Edge。Playwright 自行启动/停止 15173 上的 Vite，通过 URL 等待最多30秒；`reuseExistingServer=false`、strictPort 避免误用其它进程。桌面/手机使用同一 baseURL，失败保留 trace，测试截图位于忽略的 `frontend/test-results/`。T01 不启动 API 来测试业务，不拦截虚构业务请求。后续真实 API 浏览器测试应增加 API health 等待，并采用上述隔离库与 fixture。

T01 不提供 seed/reset/fault 控制路由。T03 若加入故障控制，仅允许 mock + TEST_ONLY 服务；生产不能注册这些路由，不能用生产 API 执行测试清库。

## 平台契约生成

唯一手写 DTO 来源为 `backend/app/common/types.py` 与相邻错误/健康模型。`contracts/openapi.json` 由应用 OpenAPI 生成器产出，共享 DTO 显式注册到 components；尚未实现的业务 API 不伪造路径。所有未来时间字段使用带时区的 `Timestamp`（Pydantic AwareDatetime），积分为严格非负整数，分页统一 cursor/limit。

```powershell
& $uvT01 run --frozen --project backend python backend/scripts/export_openapi.py
& $pnpmT01 --dir frontend contracts:generate
& $uvT01 run --frozen --project backend python backend/scripts/export_openapi.py --check
& $pnpmT01 --dir frontend contracts:check
```

生成器显式隔离调用者环境，不联网/连接数据库，JSON 排序且使用固定换行；TypeScript 由锁定 openapi-typescript 生成。修改 DTO 后两份产物同批更新，禁止手改 `frontend/src/types/contracts.ts`。`--check` 对缺失或过期产物退出1，可接入 CI。

## 停止与清理

结束自己打开的 Vite/API 终端；Compose 前台用 Ctrl+C 停止本项目服务，或在另一终端运行 `wsl.exe -d Ubuntu-24.04 -- docker compose -f /mnt/f/Work/电商/web/infra/compose.dev.yaml down`。默认保留 MySQL、Redis 和测试依赖卷。不要使用全局 prune、不要 `wsl --shutdown`，也不要删除未知卷。测试探针自动回滚/清理，不需要手工清库。
