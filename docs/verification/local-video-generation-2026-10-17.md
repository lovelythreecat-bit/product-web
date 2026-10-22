# 工作台与 videoAgent 对接排查及修复

日期：2026-10-17。状态：用户已明确批准现有凭据接入、切换真实模式及可能产生费用的短视频验收；本地真实链路已完成。用户允许调整两个项目中不合理的对接代码。本轮不变更首页、工作台布局、收费确认或方案确认操作。该结果不是生产上线验收。

## 接入前的实际阻塞

1. web 的视频连接指向 `http://127.0.0.1:8015`，保存的是业务 Token，没有管理 Token。业务 API、live、ready 均成功；管理接口实际返回 403。原 HTTP 客户端统一报“服务暂不可用”，无法定位到管理 Key。
2. videoAgent HTTP 服务的数据库仍为初始 `fake` 模式，planner/video 没有真实模型绑定。已有真实配置位于 `F:/Work/电商/videoAgent/.video-agent/config.json`，其中分镜为 `openai_chat / gpt-4o-mini`，视频为 `wan / wan3.0-video`；它与 API 使用的数据库配置相互独立。未在本文件或工具输出中记录密钥。
3. web 本地 mock / TEST_ONLY 配置未登记视频 Agent 的 D-01、D-03 和容量估计，现有 `PolicyService.require_feature` 拒绝视频生成。仅保存连接不能解除此受理门槛。
4. videoAgent 支持关闭视觉检查，导出后会返回 `quality_status=not_assessed`；web 原先只接受 `passed`，导致这种合法配置下的成片始终无法收回。
5. 管理页面把连接、模型和运行配置当作一组读取，管理接口失败时连已保存的连接地址也不展示。上游上传超限 413 也被 HTTP 客户端错误归为 503。
6. 真实出片后发现，共享文件校验的累计解码预算只有 2 亿像素；1080×1920、30 fps、5 秒就有 311,040,000 像素，合法成片因此进入 SAVE_RECOVERY。此前小尺寸替身测试没有暴露此问题。

## 代码修复

- `backend/app/agents/media_http.py`：401、403 返回固定、脱敏且可操作的 Key 配置说明；413 保留文件超限状态。仍禁止重定向，不回显上游响应正文或密钥，不自动重放请求。
- `frontend/src/features/admin/VideoAgentConfigs.vue`：先独立读取并展示连接，再读取上游模型和运行配置。管理失败时保持连接可见、可编辑，保存后重新读取。
- `videoAgent/video_agent/models.py`、`service.py`：成片增加 `visual_check_enabled: bool | null`，从对应 task + plan + generation 的持久配置快照计算；不使用当前管理设置，不解密模型密钥，不需要数据库迁移。替身或明确关闭检查为 false，启用为 true，未知历史快照为 null。API 字段说明同步。
- `backend/app/agents/video.py`：接受质量检查通过的原成片，或生成时明确关闭检查的 `not_assessed` 原成片。检查开启但执行失败、未知历史检查配置、flagged、错任务/错方案/错生成及重复匹配仍不交付。没有将“关闭检查”标记成“审核通过”。
- `backend/app/storage/validation.py`：视频累计解码预算单独设为 20 亿像素，覆盖 30 秒、30 fps 的全高清横竖屏。图片/动画原限制不变；视频单帧尺寸、帧数、完整容器检查、单线程解码、15 秒子进程超时、12 秒 CPU 与 768 MiB 内存隔离仍保留。先以真实编码的 5 秒竖屏和 30 秒横屏复现失败，再验证通过；35 秒全高清视频仍被累计预算拒绝。

后者是本次允许修复的对接兼容行为，覆盖历史对接文档中一律要求 `passed` 的技术限制；没有放开未知结果或失败检查，也没有新增人工接受操作。费用仍为原任务冻结、完整结果落盘后结算；刷新和轮询不自动确认方案，重复确认复用原生成。

## 本轮验证

新增用例均先复现失败，再验证修复。

- web 视频适配、媒体传输、视频命令、管理配置和跨项目链路：99 项通过。
- 跨项目测试使用两边实际生产模块、临时 SQLite、随机 loopback 端口和真实 HTTP；上传图片、创建/查找原任务、读取方案、显式确认、重复确认、重建适配器恢复、FFmpeg 编码、下载及 SHA256 核对通过。导出为 180×320、150 帧的真实 MP4，仅使用替身视频提供器，没有请求付费供应商。这个测试不证明平台 MySQL 作品/账本已完成真实出片验收。
- videoAgent 新增 4 项 API 回归覆盖 fake、real 关闭检查、real 开启检查和未知旧快照；其初次失败均为缺少新字段。最终上游任务、素材、鉴权、检查开关和真实编码相关 34 项通过。存在 Starlette 的 httpx 弃用提示，没有将提示描述为产品失败。
- 前端相关单测 14 项通过；完整前端 224 通过、2 失败。失败均在 `tests/unit/user-identity-display.spec.ts` 的用户管理读取/待核对赠分夹具，本轮没有修改该组件或夹具。
- 前端类型检查和生产构建通过。
- 本次修改的共享 HTTP 客户端和新增跨项目测试 Ruff 检查通过；最终 HTTP 配置/传输相关 44 项再次通过。
- 新增真实全高清解码回归后，文件校验相关 18 项通过，Ruff 通过。直接对本条真实供应商成片执行原校验先拒绝、修复后通过；未因此再次请求供应商生成。
- 桌面 1440×1000、手机 390×844 的新浏览器回归 2 项通过：管理失败仍显示连接、打开原连接抽屉、只补管理 Key、保存后读取模型恢复、页面无横向溢出。使用明确的 TEST_ONLY 接口数据，截图在 `screenshots/video-integration-recovery-2026-10-17-{desktop,mobile}.png`；已查看截图。初次测试误用了被其他静态服务占用的 15174 端口，改为本项目独立预览 15185 后通过。
- web 最终完整后端：580 通过、472 跳过、3 失败。失败为 `test_display_numbers.py::test_task_projection_preserves_number_across_state_changes_and_replay`、`test_display_numbers.py::test_task_detail_contains_persisted_owned_conversation_number`、`test_generation_parameters.py::test_original_admitted_intent_replays_without_using_new_prices`；均为旧夹具未提供任务时间字段，既有视频配置验证记录也已登记这三项。
- videoAgent 完整测试：359 通过，65 项 MySQL 测试因未提供独立 `VIDEO_AGENT_TEST_DB_*` 配置而在 setup 阶段报错。没有使用业务库冒充隔离测试库。
- Chrome DevTools 连接超时；本轮浏览器回归实际使用 Playwright / Edge，未将 DevTools 失败当作成功。

## 已执行的本机接入

用户于本轮明确选择“批准接入并验证短视频”。随后加密补齐管理 Key，通过实际 API 导入原分镜/万相配置，并切到 real；上游配置修订为 6。追加本地 `TEST_ONLY_local_video_20261017` 的 D-01 / D-03 / D-10 政策和视频 60 MiB 估计，保留原文案 8 MiB、图片 60 MiB 预留与原价格、账户/服务器配额。旧任务的政策、路由和费用快照未改写。

忽略目录中的运维脚本和执行情况：

- `.local-data/repair-video-integration-20261017.py`：已先只读预览，再按授权执行 `--apply`，通过正式管理 API 保存模型并记录平台审计。首次数据库超时后核对连接版本未变、确认回滚，再执行成功；没有盲目覆盖。
- `.local-data/enable-video-generation-20261017.py`：已先校验并回滚，再执行 `--apply`。它仅追加新任务设置，允许有原上游 ID 的 RUNNING / INVESTIGATING 任务继续轮询；不停止进程，也不改变其快照。
- `.local-data/reload-video-integration-20261017.py`：按原启动参数和进程归属校验重载 web API、视频 API 和平台 Worker。停止轮询 Worker 前锁住任务行，确认都已有原上游 ID，保留租约自然到期。运维取锁使用有界等待，未强行解锁或重提旧任务。全套服务 ready 通过，文本/图片服务及视频 Worker 复用。
- `.local-data/verify-video-workspace-20261017.py`：正式 HTTP 验收，仅创建一个独立测试账户和一个视频任务，持久化加密幂等回执，可继续查询同一任务。曾因瞬时数据库读取超时退出，恢复后仍使用原任务；只对 GET 做有界重试。账号凭据和会话未写成明文。
- `.local-data/verify-video-browser-20261017.cjs`：实际浏览器验收脚本，只在内存中接收测试会话。

## 真实短视频验收结果

测试账户：`video_verify_20261017_201045`。使用自行绘制的白色杯子联调示意图，没有上传其他用户的素材。实际调用已有 `gpt-4o-mini` 分镜和 `wan3.0-video` 视频服务，确认 5 秒、单镜头原方案。

| 项目 | 结果 |
| --- | --- |
| 平台任务 | `8c5ae797-ec01-41a4-a555-4c750d7c6ffa`，显示编号 `T20261017-000003` |
| 上游任务 | `e0a607b6-7b0f-45dd-918b-1c1b19b84341` |
| 正式作品 | `0803da85-541a-4d5d-b450-4a7a6f7f09e1` |
| 正式文件 | `e3857bff-e9d2-4608-828f-c6a21547ee1b` |
| 视频 | 1080×1920、150 帧、5 秒、H.264 MP4，6,246,037 字节 |
| 摘要 | `bee362156b141691069f618306b33a3d8a2d26b91868a215cbdff07d39ab9f5b` |
| 最终状态 | SUCCEEDED / CONSUMED |
| 生成次数 | 上游提交记录 1 条；重复受理返回原任务，方案确认未再次冻结积分 |
| 积分 | 测试账户从可用 1000 / 冻结 0 / 消费 0，变为可用 950 / 冻结 0 / 消费 50；原任务仅 freeze=50、consume=50 各 1 条，无 release |
| 质量配置 | not_assessed / visual_check_enabled=false；生成时主动关闭检查，未伪称审核通过 |
| 下载 | 作品正式接口的完整下载及 Range 0–127 校验通过；本地完整文件 SHA256 一致 |
| 桌面与手机 | 实际任务页均完整播放到结束，作品预览弹窗、下载成功，无 pageerror、无横向溢出 |

保存阶段先出现合法视频被解码预算误拒绝，修复后由原任务保存恢复完成；没有新建视频任务或再次请求供应商生成。供应商的实际货币计费未查询账单，50 是平台测试积分。

实际工作台截图已查看：`screenshots/video-workspace-live-2026-10-17-{desktop,mobile}.png`。浏览器在完整播放后定位到已解码画面截图。验收 MP4 与脱敏账本报告保存在忽略目录 `.local-data/video-workspace-verified-20261017.{mp4,json}`；浏览器结果为 `.local-data/video-workspace-browser-20261017.json`。

联调期间本机 MySQL 出现过瞬时 3 秒读取超时；运维取锁改用有界等待，正式 API 的数据库超时配置未在本轮扩改。最终正式读写、作品下载及桌面/手机完整播放均通过；这不代替数据库并发/性能验收。前述既有测试失败与缺少独立 MySQL 测试配置也未被标记为已解决。

自动审批最初因凭据写入及 `fake → real` 可能产生费用而拒绝执行；收到用户明确批准后，按同一授权范围继续完成。未绕过审批；本地 TEST_ONLY 接入不改变生产政策确认状态。
