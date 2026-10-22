# 快速生成实施与验证

原型与开工日期：2026-10-18；验证收尾：2026-10-19。依据：用户要求按 `docs/design/quick-generation-2026-10-18/` V1.1 原型实施；计划见 `docs/superpowers/plans/2026-10-18-quick-generation.md`。

## 实现

- 工作台“快速生成”入口、桌面最近任务中的流程入口及手机历史选择器；`/workspace/quick` 可新建或继续保存的流程。
- 四步复用既有商品动态表单、6 项文案参数、平台枚举、参考图片上传、视频首帧及创作指令。商品编辑保存生效、取消不保存；抽屉禁止 Escape。
- 文案完整可编辑和复制，确认版本传入图片/视频任务的不可变指令，原作品不被改写。
- 图片默认不选平台/内容，可组合主图 1 张、详情图 3 张、商品长图 1 张；费用弹窗列明各任务和合计。已释放的失败项可独立重新报价，保留成功项；未释放失败项使用既有重试/释放动作。
- 视频复用真实首帧校验、只读方案、二次确认与补资料；确认方案不再收费。完成后汇总当前确认文案、全部图片及视频，原始任务仍可从历史和作品读取。
- 新增 `quick_generation_runs` 和 0033 迁移。流程、草稿、人工确认内容、任务关联及不可变批次保存在数据库；版本号防止覆盖其他窗口进度。上游资料改动使下游确认失效，历史任务及积分记录保留。
- 图片组费用受理共享一个事务；受理失败整批回滚，受理成功后各任务独立执行/结算。服务端生成固定幂等键，丢失响应继续核对原批次。取消与提交按账户/流程锁串行，已提交任务不会被“取消费用确认”撤销。
- 轮询不覆盖较新的保存/确认，任务卡跟随真实重试后继重建，切换流程先保存草稿，商品保存响应绑定发起流程。
- 流程记录随服务端版本更新；后台任务结算变化后刷新账户余额，读取失败在后续轮询重试。

## 实际验证

| 检查 | 结果与边界 |
| --- | --- |
| 原型实际点击 | 商品抽屉取消、禁止 Escape、10 类商品、文案确认、三类五张图片及示例 60 积分清单已核对；原型数值不进入运行默认 |
| 后端定向回归 | `pytest tests/unit/test_quick_generation.py tests/unit/test_failed_task_actions.py tests/unit/test_generation_parameters.py -q`：43 passed |
| 新增前端测试 | `quick-generation.spec.ts`、`quick-product-editor.spec.ts`：8 项；连同最近任务、导航与新建任务的最终定向回归共 26 passed，覆盖人工确认、文案保留、受理不明恢复、旧轮询拦截、切换保存、费用取消、过期商品保存响应及结算后余额更新 |
| 桌面/手机完整流程 | `playwright.quick.config.ts`：2 passed，1440×1000 / 390×844；费用取消不生成、人工编辑文案、5 张图片、上传首帧、方案二次确认、汇总与刷新恢复，无页面脚本错误与水平溢出，桌面底部操作在视口内 |
| 浏览器数据边界 | 使用 TEST_ONLY 合成接口、既有设计图片和方案；验证真实 Vue/Element Plus 页面交互，没有调用真实 Agent 或消费账户积分。视频文件为合成接口占位，不据此声称真实视频播放验收 |
| 真实 MySQL 持久化 | 外层回滚事务内验证创建、保存、另一个 Session 重读、非所有者 404、旧版本 409、真实目录报价和取消；测试记录最终全部回滚，未提交生成任务 |
| 本地运行 | 0033 迁移已应用，继承既有 `utf8mb4_bin`；API 已重载，ready 200、未登录快速生成接口 401、前端入口 200；测试账户残留 0 |
| 类型/构建/接口 | TypeScript 检查、Vite 构建及 OpenAPI/TypeScript 契约一致性检查通过 |
| 设计检查 | Impeccable detector 返回空数组；独立代码复核的问题已修正并获 feature-code scope 的 ship，部分桌面/手机截图已人工查看 |

截图位于 `docs/verification/screenshots/quick-generation-{desktop,mobile}-*.png`，覆盖商品、文案、图片选择、图片成果、视频首帧、方案及完成汇总。

## 全量回归中已有的未通过项

本轮完整回归记录：后端单元测试 622 passed / 2 failed；前端 288 passed / 2 failed（允许本机回环连接后）。以下测试及对应业务文件不在本次实现范围，没有修改它们来掩盖失败：

- `backend/tests/unit/test_display_numbers.py::test_task_projection_preserves_number_across_state_changes_and_replay`：旧夹具缺少 `created_at`。
- `backend/tests/unit/test_display_numbers.py::test_task_detail_contains_persisted_owned_conversation_number`：旧任务夹具缺少 `created_at` / `updated_at`。
- `frontend/tests/unit/user-identity-display.spec.ts::shows accounts in user lists, details and recipient options without UUID fallbacks`。
- `frontend/tests/unit/user-identity-display.spec.ts::keeps an unknown pending grant inspectable without exposing its internal recipient`。两项读取用户列表时落入未模拟的网络调用。

最初沙箱内的网络运行时测试另有权限失败，已在允许本机回环的环境重跑，相关运行时项通过。快速生成新增测试及相关定向回归通过，不能据此称整个仓库全量测试通过。

未执行真实 Agent 的整条收费生成链路，也未发布到生产环境。

## 2026-10-19 入口导航卡死修复

- 复现：`/workspace/quick` 没有打开具体流程时，空草稿与空字符串基线不相等，被误判为未保存修改。离开或切换路由时试图保存不存在的流程，显示“请重新读取最新进度后继续。”，重新读取后再次导航仍会被拦截。读取流程失败时也有同样问题。
- 修复：只有已读取具体流程时才判断草稿是否修改；入口、加载中和读取失败状态不尝试保存不存在的流程。已有草稿保存失败仍阻止导航并保留文字，原有版本冲突保护继续有效。
- 回归：先观察新增入口与读取失败两项测试失败，再实施修复；快速生成、商品编辑、工作台入口与新建任务定向单测共 **16 passed**。桌面与手机入口导航加既有完整快速生成流程共 **4 passed**，TypeScript 检查及 Vite 构建通过。浏览器流程测试使用 TEST_ONLY 合成接口，没有调用真实 Agent 或消费积分。
- 真实页面：在原先报错的已登录标签页确认可打开历史任务、进入已保存快速生成、保存退出。另发现历史任务的报价请求仍返回 `500 INTERNAL_ERROR`；本次导航修复不证明真实报价或收费生成可用，服务端异常另行排查。
- 新增入口截图：`screenshots/quick-entry-navigation-desktop.png`、`screenshots/quick-entry-navigation-mobile.png`。

## 2026-10-19 商品资料保存超时修复

- 现场证据：本机 `POST /api/v1/products/versions` 多次约 3 秒返回 500，日志为 MySQL `OperationalError 2013`。回滚复现定位到 `CatalogService._principal` 获取用户行锁；数据库锁表显示 Worker 持有该用户排他锁，其他写操作等待。同账户两个进行中任务分别积累约 23 万条轮询证据，`CallbackService.import_observations` 在持锁事务中读取、解析和比对全部历史。
- 修复：历史证据改为独立只读 Session 流式读取，每批 100 条；内容摘要和重复比对在账户写锁之外执行。每条需要导入的观察独立使用短写事务，继续校验用户／任务、租约和不可变身份。仅在事务提交成功且回执为 ACCEPTED／DUPLICATE 后跳过相同内容；不同身份、结果和未成功导入的观察继续逐条核验。未删除证据、修改原任务输入、重发生成或调整积分，不新增数据库迁移。
- 回归：新增单测先在旧实现下复现持锁扫描失败，修复后并发扫描、失败重复重检、鉴权、快速生成共 **32 passed**。独立测试库的既有回调集成 **32 passed**；新增真实商品保存与历史扫描并发集成 **1 passed**。定向 Ruff 检查通过。未重跑全仓库测试。
- 本机生效：仅重载已核验归属的 Web Worker，保留原队列、消费组和 4 并发配置，API 与 Agent 服务继续运行。使用本地 mock 数据库，在外层回滚事务内通过真实 FastAPI 路由、鉴权及 CSRF 连续三次验证创建商品版本、读取版本、关联原快速生成草稿与重读流程，分别 **0.625 / 0.094 / 0.094 秒**，全部通过；临时登录会话、测试商品和流程修改全部回滚。没有在用户浏览器点击保存，也没有执行真实收费生成或生产发布。
- 独立复核：未发现本次局部修改的阻断问题。补充确认查询在 Select 上配置 `execution_options(yield_per=100)`，使 PyMySQL 使用流式游标；最终版本重跑上述 32 项单测及两项关键数据库集成通过，再次重载 Worker 后，真实保存／重读三次为 **0.485 / 0.094 / 0.093 秒**，仍全部回滚。
