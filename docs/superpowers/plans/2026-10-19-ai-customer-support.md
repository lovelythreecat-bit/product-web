# AI 客服开发计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 本计划默认由当前代理顺序执行，不自行创建子代理；用户明确选择分工后再改用 subagent-driven-development。

**Goal:** 为已登录用户提供悬浮 AI 客服弹框、持久化问答和转人工能力，并在后台查看及接待客服对话。

**Architecture:** 在现有平台增加独立 support 领域、MySQL 数据表及专用 SSE；REST 写入消息，独立客服 Worker 调用知识问答模型并条件发布完整答案。客服状态、权限和模型预算独立于创作任务与账本；人工接管使原 AI 作业失效。

**Tech Stack:** 现有 Vue 3 / TypeScript / Element Plus、Python 3.12 / FastAPI / SQLAlchemy / Alembic、MySQL 8.4 / Redis / httpx；首版不增加 WebSocket、Celery 或向量数据库。

**Spec:** [可行性评估与方案草案](../specs/2026-10-19-ai-customer-support-design.md)。执行前同时读取该文件、`AGENTS.md` 引用的本次适用设计来源与 `docs/development/frontend-ui.md`。

状态：2026-10-19 已生成、待用户评审；未开始编码。首版只支持已登录用户已确认，其他推荐决策见方案第 10 节。用户本轮明确要求“可行就生成开发计划”，所以本轮直接交草案，不另设文档生成审批。

## Global Constraints

- 客服只支持已登录用户；后台页面不显示用户客服弹框，退出/切号清空客户端客服状态。
- 客服独立于商品创作会话、生成任务、作品与积分账本；推荐不扣创作积分，待本计划审阅确认。
- 知识只有已发布版本参与回答；不导入整份历史仓库文档、不赋予 AI 业务工具权限。
- 普通 admin 不自动获得客服内容权限；新增客服名单授权仅覆盖客服对话，不改变原用户内容访问边界。
- 人工接管、转人工、释放、结束必须更新 routing_epoch；过期/失效 AI 结果不得发布。
- MySQL 为事实源；SSE、Redis 和浏览器连接生命周期不决定会话及作业是否完成。
- UI 沿用 V2 暖色、公共 UiButton/UiInput/AppDialog/AppDrawer；禁止 Esc 和遮罩关闭，触屏操作至少 44px。
- 先补并确认新增客服原型及高保真，再编码对应 UI；不修改既有业务流程或全站品牌规范。
- 不进行真实付费模型探测、生产启用、部署或历史内容删除，除非后续用户明确授权对应动作。
- 实施前重查未提交改动和 Alembic head；只提交本功能明确文件，禁止 git add . 覆盖其他工作。

## Review Focus

- 多标签页发消息或重复点击：同键不重复消息，不同键有在途 AI 时保留输入并拒绝冲突；测试归 Task 2。
- 模型仍在返回时接管、停用账户或释放客服：AI 结果失效，旧接待人不能回复；测试归 Task 2/4。
- SSE 重连及切号恰逢旧请求完成：不串号、不重提，读取 MySQL 补齐；测试归 Task 5/6。
- 知识撤回、引用伪造和提示注入：不使用撤回知识处理新作业、不输出越界来源、不执行业务动作；测试归 Task 3/4。
- 无人在线、Redis/模型故障、预算耗尽：人工队列及历史可恢复，不显示虚假在线或重复模型费用；测试归 Task 4/5/7。

## 依赖、目录与阶段

Task 0 是新增界面设计前置；Task 1→2→3→4→5 顺序形成服务端能力，Task 6/7 在设计确认和接口稳定后落地双端，Task 8 做集中联调和启用准备。首个可用里程碑为 Task 1/2/5/6/7 中的纯人工通道；AI 出现故障时同一通道仍可用，不单独分裂另一套会话系统。

新文件集中于 `backend/app/support/`、`frontend/src/features/support/`、`frontend/src/features/admin/support/`；每项功能自行携带必要配置和测试。所有下列待新增路径均为计划目标，当前尚不存在。

### Task 0：确认新增客服交互与高保真

**Files:** 新增 `docs/design/customer-support-2026-10-19/{README.md,prototype.html}` 及桌面/手机设计截图；修改仅限本方案/计划中的评审记录，不将提案写为已确认全站规范。

**Interfaces:** 输入为方案第 4 节；输出为明确版本的用户客服弹框、后台接待视图和状态说明，作为 Task 6/7 的唯一新增交互依据。

- [ ] 核对现有公共弹层与后台原型；标明客服新增入口和只作用于本功能的例外。
- [ ] 出桌面右下角入口/弹框、移动端、AI 回答/无知识/失败、待人工/离线、人工接待、已结束、未读和历史状态。展示准确文案，不用设计图替代运行页面。
- [ ] 出后台队列、会话阅读回复、知识草稿/发布/撤回及设置抽屉；核对键盘操作、焦点、滚动和费用确认弹框的层级。
- [ ] 用户审阅方案中的推荐项及具体设计版本；把答复记录在设计 README，然后开始对应界面实施。未确认项不由代理假定为新默认。

### Task 1：客服持久化、权限和接口类型

**Files:** 新增 `backend/app/support/{__init__,models,schemas,permissions}.py`、`backend/migrations/versions/<实际新版本>_customer_support.py`、`backend/tests/unit/test_support_permissions.py`、`backend/tests/integration/test_support_schema.py`；修改 `backend/app/config.py`、`backend/migrations/env.py`、`backend/.env.example`、`infra/env.example`。

**Interfaces:** `require_support_user(session, principal) -> Principal`；`require_support_admin(session, settings, principal) -> Principal`；定义方案第 5 节 11 张表和 DTO `SupportConversationView / SupportMessageView / SupportJobView / SupportBootstrapView / SupportArticleView / SupportSettingsView`。主状态为 AI_ACTIVE/WAITING_HUMAN/HUMAN_ACTIVE/RESOLVED；消息 user/ai/human/system；作业 QUEUED/RUNNING/SUCCEEDED/FAILED/OBSOLETE。

- [ ] 先写失败测试：未登录 401、非 owner 404、未授权 admin 403、已授权且停用 admin 403；客服授权不能读创作消息。数据库验证同用户双建活动会话仅一个、消息序号/AI job 回复唯一、无效外键失败。
- [ ] 在隔离 MySQL 测试库运行新测试，记录缺少 support 模块/表的预期失败，不在工作开发库或生产库运行迁移测试。
- [ ] 实现 11 表、索引/检查约束、严格 DTO 和权限。`APP_SUPPORT_ADMIN_IDS=[]` 默认无后台内容授权；增加独立加密主密钥配置但无默认 Key，保留现有 admin 角色定义。作业按问题＋attempt_number 唯一以支持重试，问题的成功回复只允许一条。
- [ ] 根据实际 Alembic head 新建唯一迁移；在隔离库验证升级及其他领域表不变，执行 `pytest tests/unit/test_support_permissions.py tests/integration/test_support_schema.py -q` 通过。
- [ ] 检查 diff，仅提交本任务文件；记录迁移版本和配置含义。

### Task 2：可靠消息、人工接管与队列状态

**Files:** 新增 `backend/app/support/{service,repository,routes,admin_routes,audit}.py`、`backend/tests/unit/test_support_state_machine.py`、`backend/tests/integration/test_support_conversations.py`；修改 `backend/app/main.py` 注册路由。

**Interfaces:** `SupportService(session, settings)` 提供 `get_or_create_active(principal, *, key)`、`send_user_message(principal, conversation_id, dto, *, key)`、`request_handoff(principal, conversation_id, *, expected_version, key)`、`claim(principal, conversation_id, *, expected_version, key)`、`reply(principal, conversation_id, dto, *, key)`、`release(principal, conversation_id, *, expected_version, key)`、`resolve(principal, conversation_id, *, expected_version, key)`、`recover_assignment(principal, conversation_id, *, reason, expected_version, key)`、`mark_read(principal, conversation_id, *, through_seq, key)`；返回 Task 1 DTO。`dto` 为对应接口的严格 Pydantic 请求模型，消息体固定 content/client_message_id；消息幂等键使用必需请求头。

- [ ] 写测试断言：同键同载荷返回同消息/会话，不同载荷 409；创建竞争不产生两个活动会话；两个客服接待仅一成功；只有接待人可回复；release 回 WAITING_HUMAN；RESOLVED 只读；关闭 UI 不调用 resolve。
- [ ] 加入并发测试：AI 有在途时第二次发送 409 且不创建第二作业；转人工与发送竞争按数据库顺序产生唯一合法状态；read_seq 单调、不能超过当前最大 seq，其他客服只读不清接待人未读。原接待人停用/撤权时，授权客服带原因可恢复为待接待；仅离线或 Redis 故障不可抢接。
- [ ] 运行新测试得到预期失败；实现短事务、统一锁顺序（用户按 ID 排序→会话→消息/作业→受众事件头）、数据库版本校验和审计，不使用长事务包外部调用。状态操作通过 support_operation_receipts 保存载荷摘要和原响应，同事务稳定重放。
- [ ] 实现方案第 8 节基础 REST、普通账户所有权、后台正文读取审计；返回必要状态不带素材/作品/创作正文，后台列表默认不带消息摘要。
- [ ] 运行上述两份新测试及现有相关 auth/admin 权限测试；通过后只提交本任务文件。

### Task 3：知识草稿、发布快照与检索

**Files:** 新增 `backend/app/support/{knowledge,knowledge_routes,knowledge_seed}.py`、`backend/tests/unit/test_support_knowledge.py`、`backend/tests/integration/test_support_knowledge_publish.py`、`docs/support/faq-draft-2026-10-19.md`。

**Interfaces:** `KnowledgeService(session)` 提供 `save_draft(principal, article_id, dto, *, expected_version, key)`、`publish(principal, article_id, *, expected_version, key)`、`withdraw(principal, article_id, *, expected_version, key)`、`search(question: str, *, limit: int = 6) -> list[KnowledgeSnippet]`；`KnowledgeSnippet={article_id,revision_id,title,body,source_note}`，`search` 只返回当前已发布头。

- [ ] 写失败测试：草稿不可搜、撤回不参与新搜索、历史引用保留、并发编辑 409、发布幂等；中文标题、同义问法和正文检索顺序稳定；无命中返回空。
- [ ] 运行测试确认失败；实现标题/关键词优先和正文召回，权重/阈值通过固定中文样本验证，不用不存在的“模型置信度”代替检索。固定最多 6 条、每条 1500 字、总知识 9000 字；仅精确标准问法可直接返回正式答案。
- [ ] 整理 30–50 条 FAQ 草稿，标明现行依据；测试/历史价格、已撤回规则和秘密不导入。提供显式导入草稿命令，不自动发布。
- [ ] 实现知识 CRUD、发布/撤回接口、版本和审计；运行上述两份新测试通过，仅提交本任务文件。知识内容审阅列入 Task 8，不自行宣称已批准。

### Task 4：独立问答模型、预算与可恢复 Worker

**Files:** 新增 `backend/app/support/{configuration,provider,answering,jobs,budget,settings_routes}.py`、`backend/worker/support.py`、`backend/tests/unit/{test_support_provider,test_support_answering}.py`、`backend/tests/integration/test_support_jobs.py`；使用 Task 1 的预算及幂等表，不改已部署迁移。

**Interfaces:** `SupportProvider.answer(request: SupportAnswerRequest) -> SupportAnswerResult` 异步；结果字段 answer/disposition/citation_ids/usage。`SupportJobRunner.tick() -> JobTickResult` 为 Worker 单次操作；`publish_answer(session, job_id, lease_token, result) -> bool` 完整条件发布。`SupportSettingsService.read_public()`、`read_admin(principal)`、`update(principal, dto, *, expected_version, key)`；`BudgetService.reserve(call_id, max_tokens)`、`reconcile(call_id, usage)` 原子幂等，call_id 统一覆盖作业和显式连接测试。

- [ ] 写失败测试：无知识不调模型；只发本会话最近最多 12 条/6000 字及已发布知识；错误引用、无效 JSON、HTML/脚本按纯文本或降级；索要 Key/退款不获得任何工具；超时 30 秒、响应 128 KiB、答案 4000 字边界。
- [ ] 测试连接加密/只写、相同服务留空保留 Key、更换服务必须新 Key、配置版本变化使旧排队作业安全失败；保存配置不自动探测；缺 Key/知识/预算时 AI 关闭但人工可用。测试非法 URL、云元数据 IP、DNS 解析到禁用网段、重定向和 DNS 重绑定，必要时将连接绑定至已校验解析目标。
- [ ] 测试接管后迟到 AI、账户停用、lease 过期或旧 token 发布均不入时间线；重复发布唯一回复；调用外部模型时不占用数据库事务；Worker 崩溃恢复不自动重调模型；显式 retry 不重复用户问题且同键只有一个新作业。
- [ ] 测试 UTC 日界预算预留并发不超限，按 usage 结算一次，无 usage/调用结果不明保留保守预留，重启不重置；单用户每分钟 6 次与单会话一条在途独立生效。模型连接测试也计入预算；多个 Worker 合计最多 4 个 RUNNING 调用，不能各放出 4 个。
- [ ] 运行新测试确认失败，实现 provider、发布条件、作业扫描和独立 Worker。预算与回执使用 Task 1 独立表，不挪用积分表；领取时统一数据库锁保护全局并发初值 4，输出 token 建议上限 1500，输入按真实模型窗口预算。
- [ ] 运行 provider/answering/jobs 新测试，使用受控 HTTP mock 和隔离 MySQL。验证禁用 AI 时 Worker 不调模型，人工流程仍通过；仅提交本任务文件。

### Task 5：客服专用 SSE、恢复、限流与在线状态

**Files:** 新增 `backend/app/support/{events,event_routes,presence}.py`、`backend/tests/integration/test_support_events.py`、`backend/tests/unit/test_support_degradation.py`；修改 Task 2 路由接入同事务事件。

**Interfaces:** `append_support_event(session, *, audience_key, event_key, kind, payload)`；GET `/support/events` 与 `/admin/support/events`，Last-Event-ID/after 绑定受众；`PresenceService.heartbeat(actor, on_duty)` / `status()`，Redis heartbeat 15 秒、TTL 45 秒。

- [ ] 写失败测试：消息/状态事务回滚不产生事件；不同用户游标 reset 不泄露；重连只补持久化事件；每次投递重新检查 session 与客服名单，撤权/停用后停止。
- [ ] 测试 Redis 故障时在线 unknown、AI 受理暂拒但历史/转人工/人工回复可用；数据库保底限流保护人工写入。慢 SSE 客户端不持有数据库连接；心跳不修改 assignee；45 秒无心跳显示离线。
- [ ] 运行测试确认失败；实现独立 support 事件表、序号、无正文通知、快照恢复。SSE 连接数限制与心跳纳入部署配置，不扩展 task.updated 或原事件 DTO。
- [ ] 运行新测试，回归 `backend/tests/unit/test_event_updates.py` 及既有事件集成测试的实际文件；通过后提交限定文件。

### Task 6：用户悬浮入口、弹框与身份安全

**Files:** 新增 `frontend/src/api/support.ts`、`frontend/src/features/support/{SupportWidget,SupportPanel,SupportMessageList}.vue`、`{store,useSupportStream}.ts`、`support.css`、`frontend/tests/unit/{support-widget,support-identity,support-stream}.spec.ts`；修改 `frontend/src/App.vue`、`components/AppDialog.vue`、`AppOverlay.vue`、`styles/element-components.ts`（实际需要时）、`tests/unit/overlays.spec.ts`。

**Interfaces:** `useSupportStore()` 暴露 bootstrap/open/close/send/handoff/retry/resolve/markRead/loadHistory；`useSupportStream({onUpdate,onReset})` 返回 stop。请求统一复用 `api/client.ts`，DTO 从 OpenAPI 生成；局部状态关联 session.epoch，开关只控制显示不触发会话结束。

- [ ] 依据 Task 0 确认稿写组件测试：已登录用户页面只有一个入口、未登录和后台无入口、跨路由保持、打开不创建空会话、关闭保留已发送消息、草稿及在途作业，重新打开读取最新结果。
- [ ] 测试同一发送意图保留 body/key，失败/结果不明只 GET 核对或同键显式重试；AI 有在途时禁止重复发送但可转人工；人工未读按真正可见消息推进。SSE 断线前台 5 秒 GET，隐藏暂停，恢复去重。
- [ ] 测试退出/切号同时到达旧响应：停止 SSE、取消请求、清空草稿和游标，epoch 不符不落新状态；同用户换路由不清空会话。
- [ ] 运行新测试确认失败；实现业务组件和 AppDialog 可选 `placement='center'|'bottom-right'|'bottom-left'` 及命名业务 footer 插槽，默认保持原行为。复用 ElDialog，不新建另一套弹层系统；手机采用确认稿中的近全屏样式。
- [ ] 测试旧费用确认/删除/编辑弹层仍居中，Esc 不关闭、焦点恢复；打开高优先级弹层收起客服并保留草稿，不产生双重焦点陷阱。运行 support、overlays、ui-controls 定向单测及 typecheck，通过后提交限定文件。

### Task 7：后台客服中心、知识管理与设置

**Files:** 新增 `frontend/src/api/adminSupport.ts`、`frontend/src/features/admin/support/{SupportCenterView,SupportQueue,SupportConversation,SupportKnowledge,SupportSettings}.vue`、`frontend/tests/unit/admin-support.spec.ts`；修改 `frontend/src/router.ts`、`components/AppShell.vue`、按需 `components/AppIcon.vue`。

**Interfaces:** `/admin/support` 及三个子视图，使用 Task 2–5 接口和 Task 6 共用的纯消息渲染组件；导航仅在 bootstrap 返回客服权限时显示，后端权限仍为最终边界。

- [ ] 写失败测试：普通 admin 无入口且直接 URL/API 仍被拒；授权客服可查 AI/待接待/人工/结束会话；列表不带正文；只读查看不获取回复权；抢接 409 保留草稿、刷新接待人。
- [ ] 测试值守/离线及后台站内提醒、无客服在线时前台保留留言；接待人释放/权限被撤回后原回复不可提交。不得模拟外部通知或假装对方已读。
- [ ] 测试知识草稿不生效、发布/撤回版本冲突保留输入；Key 不回显，保存/取消分离，明确连接测试才请求模型。关闭 AI 不关闭人工和会话历史。
- [ ] 运行新测试确认失败；按 Task 0 实现队列与对话、原型规定的编辑抽屉，复用游标分页、表格、按钮与主题。手机可列表→会话切换，不强塞桌面多列。
- [ ] 运行 admin-support 和受影响后台导航单测、typecheck；核对七个既有后台入口仍可达，通过后提交限定文件。

### Task 8：集中联调、知识评测与运维交付

**Files:** 新增 `frontend/tests/e2e/customer-support.spec.ts`、`frontend/playwright.support.config.ts`、`backend/tests/browser_support/support_seed.py`、`docs/support/evaluation-2026-10-19.json`、`docs/verification/customer-support-2026-10-19.md`、`infra/runbooks/customer-support.md`；修改 `backend/tests/browser_support/{seed,runtime}.py`（仅必要扩展）、`backend/scripts/export_openapi.py`（如需）、`backend/app/common/openapi.py`、`contracts/openapi.json`、`frontend/src/types/contracts.ts`、`infra/scripts/start_local.py`（可选客服进程）、`README.md`。

**Interfaces:** 现有 HTTPS TEST_ONLY harness 增加受控客服模型和两名隔离客服账号；专用 Playwright 配置只跑客服与必要弹层回归。Worker 入口 `python -m worker.support`；模型/人工健康状态独立可观察，不把 Web ready 等同客服可用。

- [ ] 用真实应用＋隔离数据库＋受控模型跑两个用户、两个客服浏览器上下文：提问→回答→转人工→抢接→回复→刷新恢复→结束→新咨询；断线只恢复，不重复请求或收费。
- [ ] 双端截图：桌面 1440×1000、手机 390×844；核对首页悬浮位置、工作台底部操作、弹框滚动、手机键盘、安全区、焦点/显式关闭、长消息和零横向溢出。
- [ ] 做故障验证：模型超时/错误、Worker 重启、SSE 失效、Redis 不可用、预算耗尽、管理员停用、用户切号、知识撤回。分别记录人工通道与 AI 通道真实结果。
- [ ] 人工审阅 FAQ 草稿并发布已确认条目；建立至少 80 问评测集，按方案第 9 节逐条核查。真实模型验收需后续用户授权调用；未授权只报告受控模型流程结果及真实语义质量未验。
- [ ] 同批重新导出 OpenAPI/TypeScript；运行下方必要命令。记录通过/失败/未运行和已有无关故障，不用 build 代替语义、权限或视觉验收。
- [ ] 运维手册记录迁移、独立 Worker 启停、配置和客服授权、日志/告警、每日预算、备份恢复及开关回退。人工入口与 AI 分别启用；回退关闭 AI 不删除会话。待保留期确认后补清理实现和验证，再允许生产启用。
- [ ] 若用户要求本地启动器集成，仅在显式启用客服配置时拉起专用 Worker；原启动流程不依赖未配置模型，不自动发送探测或迁移。测试启动器可选性并核对其他服务仍复用。
- [ ] 仅提交客服相关文件；交付设计对照、接口/迁移说明、测试证据、模型用量与仍未确认的启用项，不自行部署或宣布生产验收。

## 验证命令与环境

命令由实施阶段执行；**本次计划交付没有运行功能测试**。后端命令从 `backend/` 执行，使用该项目 uv 锁定环境或 `backend/.venv`；数据库集成测试只指向独立 TEST_ONLY 数据库。前端命令从仓库根执行。若 PATH 工具失效按 `docs/development/t01-bootstrap.md` 定位已安装工具，不因此重装。

```powershell
# backend/，先逐任务运行，收尾仅补尚未覆盖的相关回归
uv run --frozen pytest tests/unit/test_support_permissions.py tests/unit/test_support_state_machine.py tests/unit/test_support_knowledge.py tests/unit/test_support_provider.py tests/unit/test_support_answering.py tests/unit/test_support_degradation.py -q
uv run --frozen pytest tests/integration/test_support_schema.py tests/integration/test_support_conversations.py tests/integration/test_support_knowledge_publish.py tests/integration/test_support_jobs.py tests/integration/test_support_events.py -q
uv run --frozen ruff check app/support worker/support.py
uv run --frozen python scripts/export_openapi.py

# 仓库根目录
pnpm --dir frontend contracts:generate
pnpm --dir frontend contracts:check
pnpm --dir frontend exec vitest run tests/unit/support-widget.spec.ts tests/unit/support-identity.spec.ts tests/unit/support-stream.spec.ts tests/unit/admin-support.spec.ts tests/unit/overlays.spec.ts
pnpm --dir frontend typecheck
pnpm --dir frontend build
pnpm --dir frontend exec playwright test --config=playwright.support.config.ts
```

## 人日估算与完成定义

| 阶段 | 估算 |
| --- | --- |
| 方案审阅、原型及高保真 | 1–2 人日 |
| 数据、鉴权、人工会话与并发 | 2–3 人日 |
| 知识、模型、预算与 Worker | 3–4 人日 |
| 客服事件、用户端及后台 | 4–5 人日 |
| 双端联调、知识评测与运维说明 | 2–4 人日 |
| 合计 | **12–18 人日**；不含等待评审、人员值守和供应商开通的日历时间 |

完成开发须同时满足：用户批准具体新增设计；账户隔离/转接竞争/恢复测试通过；已发布知识可追溯；人工离线/模型失败可继续留存和接待；双端视觉和键盘核对；接口产物同步；限定代码评审和发现项修复。

真实服务启用另需：模型供应商与每日预算确认、语义评测达到方案目标、真实授权客服人员/值守说明落实、对话保留/删除及供应商数据说明确认并实现。计划生成、mock 通过、设计确认均不能替代这些条件。
