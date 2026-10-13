# T18 共享基础、账号 / 积分、创作工作台与作品

需求与视觉入口：`../docs/product-design.md`。Vue3/Vite依赖沿用锁定版本。注册、登录、个人中心、充值说明、创作工作台和作品消费真实接口，沿用 V2 奶油米色与陶土橙风格。实际验证范围以每次专项报告及日志为准；TEST_ONLY mock 验证不代表生产 Agent 接入或完整生产验收。

## 共享身份边界（供 T18c 使用）

`src/features/auth/session.ts` 导出 `session` 和 `onIdentityChange(listener)`；后者返回取消订阅函数。事件为 `{epoch,userId,reason}`，reason 为 authenticated / logout / unauthorized。初始登录由 GET /me 恢复，资料保存不切换 epoch。身份变更同步清空共享 profile/account 并通知订阅者，RouterView 按 epoch 重建，清空本页账本和分页游标。

创作消费者订阅身份变化，关闭 EventSource、清空用户任务 / 作品 / 会话 / 草稿与事件游标；异步处理捕获 epoch 并在回写前比较。HTTP client 对跨 epoch 的迟到响应（包括旧 401）抛出 IDENTITY_CHANGED，当前受保护请求 401 才清身份并回登录；登录 / 注册错误保留公共表单反馈。身份、密码与注册重试意图仅在内存中。创作草稿和未确认受理结果的原始 body/key 使用按 user_id 隔离的 tab-scoped sessionStorage；退出或不同身份同步删除旧草稿。原生 SSE 游标仅在当前消费者内存中，页面重载先 GET 原记录，再连接事件流。

注册网络重试保留同一原始 account/password/request_key 对象，字段编辑才生成新意图；无自动 POST 重试。退出成功须经服务端 POST 撤销；失败显示重试反馈。账户余额和累计入账全部取 GET /account，分页消费 GET /account/ledger 的不透明 next_cursor，来源任务只经本人 GET /tasks/{id} 读取。充值页仅 GET，未实现订单 / 支付。

`auth-account.spec.ts`、`auth-account-failures.spec.ts`、`account-ledger.spec.ts` 是实际点击 UI 验证（桌面 / 手机），网络故障只 abort 真正请求或丢弃真实响应，不伪造业务响应。分页场景通过真实受理 / Worker / mock 上游生成 23 条流水后，在翻页中插入第 24 条；这部分 API 准备不代表创作 UI 已实现。

- `src/styles/tokens.css`：已确认 V2 暖色语义变量。
- `AppDialog` / `AppDrawer`：受控`v-model:open`、`title`、`purpose=read|edit|charge|delete`，默认内容和`actions`插槽。read初焦标题，edit用`data-initial-focus`（否则标题），charge/delete初焦取消。内置取消和关闭按钮明确为`type="button"`，嵌入父form也只通知父层，不提交或保存业务数据；actions插槽的业务按钮由调用方显式选择`type="submit"`或`type="button"`。保存成功由调用方关闭；失败保留open与输入。原生dialog+显式Tab首尾循环，Escape和关闭恢复触发焦点；抽屉手机全屏。
- `api/*.ts`与`types/contracts.ts`：同源cookie，mutation读取当前csrf cookie；浏览器自动Origin。`createIntent(body)`在用户确认时创建，`submitTaskIntent(intent)`、`preparePrompt(intent)`显式重试复用原字符串body/key。编辑、重新生成是新意图。`submitTask(key,request)`兼容原T18接口，调用者必须保存同一key对应原body。通用client无POST自动重试、无任务状态/积分推断。
- `files.uploadFile`遵循binary请求体和display_name查询参数，Content-Type取File.type。通用client若收到FormData不写multipart边界。文件内容URL由同源受保护接口提供。
- `features/workspace/useTaskStream.ts` 使用原生 EventSource；`connectTaskEvents(after)`只发送不透明 after 游标。持久事件读取包装 payload，按 state_version 合并；临时片段独立存放且终态清除。reset 关闭连接并 GET 会话、任务详情与作品后按新游标恢复；onerror 经受保护 GET 识别失效身份，并延迟重连，恢复过程不 POST 替代任务。

## 创作与作品

每会话保存商品版本、固定素材版本和每 Agent 参数。规格字段、默认值和报价来自当前目录；正式提交前显示完整输入及固定报价，取消初焦。报价过期清空规格选择，要求重选与重新确认。网络提交结果不明时保留原 body/key，刷新后仍可核对原任务并显式重放。

TaskCard 只读取持久任务详情，执行状态与积分结算分别展示。AI 辅助在输入区预览、编辑、采用、取消和撤回，保留空原指令与 Agent 参数。作品显示完整文案或受保护图片/视频，支持详情、复制、预览、下载、筛选与游标分页。重新创作读取原作品和商品版本，创建独立会话；不可用来源素材必须补传后才能提交。删除只使用来源中记录的 D-09 版本。

`user-flow.spec.ts` 和 `material-lifecycle.spec.ts` 通过 UI 与实际 HTTPS API/Worker/MySQL/文件验证业务流程；网络故障仅丢弃真实响应或让浏览器离线。`task-stream.spec.ts` 与 `workspace-drafts.spec.ts` 是消费者契约及响应式单元测试，不作为真实浏览器通过证据。

## 真实浏览器 harness

从仓库根目录PowerShell执行（已装依赖/Chromium缓存，不下载浏览器）：

```powershell
$env:APP_MODE='mock'
$env:APP_TEST_ONLY='true'
$env:TEST_ONLY='true'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
$env:NO_COLOR=$null
$env:TEST_DATABASE_URL='mysql+pymysql://ecommerce_test:TEST_ONLY_test_local@127.0.0.1:13306/ecommerce_ai_test_t07_20261011?charset=utf8mb4'
$env:TEST_REDIS_URL='redis://127.0.0.1:16379/15'
$env:PLAYWRIGHT_BROWSERS_PATH=(Join-Path $PWD 'frontend/.cache/ms-playwright')
pnpm --dir frontend exec playwright test
```

Python使用`backend/.venv/Scripts/python.exe`，已安装项目依赖，MySQL migration须为0021_site_content。API本地18018、Vite HTTPS15173必须空闲；mock/control端口随机。没有reuseExistingServer。测试证书保存在每次独立`frontend/.cache/browser/TEST_ONLY-UUID/`，只测试忽略其信任，不改系统证书或生产安全。测试结束关闭自己创建的Vite、API、mock与worker；`startup.json`/`processes.json`记录健康与exit，保留本run磁盘/SQL业务证据，仅清本run Redis前缀。

全量后端测试和本套浏览器测试串行，因为注册测试政策head在共享mock库。每次启动建立独立账号前缀、真实服务发布的目录/TEST_ONLY政策和独立stream/group；Worker只处理通过`/register`校验过的本run账号及Agent的实际task ID。并不扫描其他任务。API无生产调试路由。

`tests/e2e/setup.ts`启动`backend/tests/browser_support/runtime.py`。Node测试端读取独立control.json随机令牌访问loopback控制服务，浏览器不接触此令牌：

| 控制 | 行为 |
| --- | --- |
| `/register` | `{task_id,scenario,paused?}`登记实际API受理ID，检查本run归属，默认常驻Worker处理。 |
| `/drive` | `{task_id}`通过真实outbox/consumer立即推进原任务一阶段；不会改任务事实、余额或发布记录。 |
| `/scenario` | `{task_id,scenario}`只修改mock网络故障；保留external/upstream身份与调用计数。`save_failure`在本任务磁盘commit抛OSError，normal移除故障。 |
| `/notify` | `{task_id,failure?}`构造固定TEST_ONLY协议的签名原上游事件，实际CallbackService验证两次，保留ACCEPTED/DUPLICATE。 |
| `/inspect` | `{task_id}`读取MySQL task/work/ledger、mock次数、磁盘hash并保存本runJSON。 |
| `/resume` | `{task_id}`恢复该登记任务常驻调度。 |
| `/reprice` | `{kind}`使用本 run 的 TEST_ONLY 管理员与 CatalogService CAS 发布新的价格版本，保留 mock 8/20/60，不重写历史。 |
| `/prune` | `{task_id}`校验本 run 归属后，以真实 retention 服务裁剪该用户事件，供原生 SSE reset 补偿验证；不改任务与账本。 |

真实浏览器 smoke 在 page.evaluate 中调用产品 API 模块；无 route.fulfill、无 APIRequestContext 伪造业务。它证明接线，具体 UI 业务流程由专项测试验证。scenario-controls 覆盖未知受理/普通 NOT_FOUND 保留冻结、原结果保存恢复、确定失败签名与重复通知、部分结果无结算；完整 F01–08 矩阵仍归 T18d。测试价格 8/20/60 及赠送 1000 仅 TEST_ONLY，不是生产数值。HTTPS Vite 测试代理传递 forwarded scheme，测试 runtime 只信任 loopback 127.0.0.1 的代理头以保留 SSE Origin 校验。

## 生命周期边界复跑

`pnpm --dir frontend exec vitest run tests/unit/runtime-lifecycle.spec.ts` 单独验证启动器实际复用的 `tests/e2e/runtime-lifecycle.ts`。这些专项仅使用自己的随机loopback端口、Vite实例和Node子进程，不访问数据库。覆盖TLS响应停滞、控制端停滞、强杀后观察exit、关闭报错仍清理子进程、正常退出及占用连接强制关闭后的完成等待。

健康请求每次最多1秒且受启动45秒总期限约束；退出在网络await之前设立5秒优雅退出期限，控制请求最多1秒，超时后只强制终止本次spawn的进程并最多再等5秒观察真实exit。Vite与子进程并行收尾，单个失败不会跳过另一个；强制关闭仅处理自有Vite连接。清理完成或报错均在finally保存`processes.json`和`runtime.log`，`exitObserved`与`cleanupError`区分已退出和清理失败；未观察到退出不会记为成功。

`pnpm --dir frontend exec playwright test overlay-form.spec.ts` 覆盖真实AppDialog/AppDrawer父form组合：四种purpose、页头/页脚、鼠标/Enter/Space，桌面和手机各48次取消/关闭无submit；调用方明确submit按钮仍提交一次。此命令须使用上面的TEST_ONLY环境。

## 2026-10-13 平台交付边界

三核心文案 / 图片 / 视频 Agent 仍调试，本次仅预留平台适配与 TEST_ONLY mock；真实接入和独立桥接均 DEFERRED_BY_USER，最新指令覆盖 10-12 桥接实施安排。协议 draft、生产关闭约束保留。原 T18～T25 聚合验收仍待完成，不把历史专项通过汇总为全量 PASS。

普通 pnpm dev 默认为 HTTP，身份 Secure cookie、Origin / CSRF 检查需要正确 HTTPS 同源配置；裸启动不能完整演示登录与生成。普通空库没有测试 harness seed 的策略、目录、管理员和存储配置，相关功能继续关闭。上方 HTTPS TEST_ONLY harness 仅用于隔离验证，本次不重跑或新增启动器。

交付入口：[仓库 README](../README.md)、[本次范围](../docs/development-scope-2026-10-13.md)、[交付清单](../docs/release-checklist.md)、[AC 追踪](../docs/verification/acceptance.csv)。
