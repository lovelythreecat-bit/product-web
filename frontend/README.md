# T18a 共享基础与 T18b 账号 / 积分

需求与视觉入口：`../docs/product-design.md`。Vue3/Vite依赖沿用锁定版本。注册、登录、个人中心和充值说明已消费真实接口；创作工作台与作品仍为明确占位，等待 T18c，不能将 API smoke 当成其 UI 业务流程验收。

## 共享身份边界（供 T18c 使用）

`src/features/auth/session.ts` 导出 `session` 和 `onIdentityChange(listener)`；后者返回取消订阅函数。事件为 `{epoch,userId,reason}`，reason 为 authenticated / logout / unauthorized。初始登录由 GET /me 恢复，资料保存不切换 epoch。身份变更同步清空共享 profile/account 并通知订阅者，RouterView 按 epoch 重建，清空本页账本和分页游标。

创作消费者须订阅身份变化，关闭 EventSource、清空用户任务 / 作品 / 会话 / 草稿与事件游标；异步处理捕获 epoch 并在回写前比较，不能把旧用户 after 用于新连接。当前阶段尚无 SSE 消费者或事件游标存储，不能宣称 T18c 已验证。HTTP client 对跨 epoch 的迟到响应（包括旧 401）抛出 IDENTITY_CHANGED，当前受保护请求 401 才清身份并回登录；登录 / 注册错误保留公共表单反馈。身份、密码与注册重试意图均只在内存中，未写入浏览器持久存储。

注册网络重试保留同一原始 account/password/request_key 对象，字段编辑才生成新意图；无自动 POST 重试。退出成功须经服务端 POST 撤销；失败显示重试反馈。账户余额和累计入账全部取 GET /account，分页消费 GET /account/ledger 的不透明 next_cursor，来源任务只经本人 GET /tasks/{id} 读取。充值页仅 GET，未实现订单 / 支付。

`auth-account.spec.ts`、`auth-account-failures.spec.ts`、`account-ledger.spec.ts` 是实际点击 UI 验证（桌面 / 手机），网络故障只 abort 真正请求或丢弃真实响应，不伪造业务响应。分页场景通过真实受理 / Worker / mock 上游生成 23 条流水后，在翻页中插入第 24 条；这部分 API 准备不代表创作 UI 已实现。

- `src/styles/tokens.css`：已确认 V2 暖色语义变量。
- `AppDialog` / `AppDrawer`：受控`v-model:open`、`title`、`purpose=read|edit|charge|delete`，默认内容和`actions`插槽。read初焦标题，edit用`data-initial-focus`（否则标题），charge/delete初焦取消。内置取消和关闭按钮明确为`type="button"`，嵌入父form也只通知父层，不提交或保存业务数据；actions插槽的业务按钮由调用方显式选择`type="submit"`或`type="button"`。保存成功由调用方关闭；失败保留open与输入。原生dialog+显式Tab首尾循环，Escape和关闭恢复触发焦点；抽屉手机全屏。
- `api/*.ts`与`types/contracts.ts`：同源cookie，mutation读取当前csrf cookie；浏览器自动Origin。`createIntent(body)`在用户确认时创建，`submitTaskIntent(intent)`、`preparePrompt(intent)`显式重试复用原字符串body/key。编辑、重新生成是新意图。`submitTask(key,request)`兼容原T18接口，调用者必须保存同一key对应原body。通用client无POST自动重试、无任务状态/积分推断。
- `files.uploadFile`遵循binary请求体和display_name查询参数，Content-Type取File.type。通用client若收到FormData不写multipart边界。文件内容URL由同源受保护接口提供。
- `types/task-stream.ts`为T18c消费者预留共享接口；`connectTaskEvents(after)`只发送不透明after游标。完整消费者、按用户清游标、reset后GET恢复和state_version合并归T18c。

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

Python使用`backend/.venv/Scripts/python.exe`，已安装项目依赖，MySQL migration须为0019_lifecycle。API本地18018、Vite HTTPS15173必须空闲；mock/control端口随机。没有reuseExistingServer。测试证书保存在每次独立`frontend/.cache/browser/TEST_ONLY-UUID/`，只测试忽略其信任，不改系统证书或生产安全。测试结束关闭自己创建的Vite、API、mock与worker；`startup.json`/`processes.json`记录健康与exit，保留本run磁盘/SQL业务证据，仅清本run Redis前缀。

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

真实浏览器smoke在page.evaluate中调用产品API模块；无route.fulfill、无APIRequestContext伪造业务。它证明接线，不代表尚未实现的注册/创作UI流程。scoped-controls覆盖未知受理/普通NOT_FOUND保留冻结、原结果保存恢复、确定失败签名与重复通知、部分结果无结算；完整F01–08仍归T18d。测试演示价格8/20/60及赠送1000仅TEST_ONLY，不是生产数值。

## 生命周期边界复跑

`pnpm --dir frontend exec vitest run tests/unit/runtime-lifecycle.spec.ts` 单独验证启动器实际复用的 `tests/e2e/runtime-lifecycle.ts`。这些专项仅使用自己的随机loopback端口、Vite实例和Node子进程，不访问数据库。覆盖TLS响应停滞、控制端停滞、强杀后观察exit、关闭报错仍清理子进程、正常退出及占用连接强制关闭后的完成等待。

健康请求每次最多1秒且受启动45秒总期限约束；退出在网络await之前设立5秒优雅退出期限，控制请求最多1秒，超时后只强制终止本次spawn的进程并最多再等5秒观察真实exit。Vite与子进程并行收尾，单个失败不会跳过另一个；强制关闭仅处理自有Vite连接。清理完成或报错均在finally保存`processes.json`和`runtime.log`，`exitObserved`与`cleanupError`区分已退出和清理失败；未观察到退出不会记为成功。

`pnpm --dir frontend exec playwright test overlay-form.spec.ts` 覆盖真实AppDialog/AppDrawer父form组合：四种purpose、页头/页脚、鼠标/Enter/Space，桌面和手机各48次取消/关闭无submit；调用方明确submit按钮仍提交一次。此命令须使用上面的TEST_ONLY环境。
