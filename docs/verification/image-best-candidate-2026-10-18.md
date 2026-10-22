# 图片选优交付与原任务恢复

2026-10-18，按用户确认的“生成出图后，最大修复次数用尽仍返回最高分候选，不因审核不通过失败”实施。图片服务、Web API 和平台 Worker 已安装并重载。本记录不代表完整生产验收。

## 已实现

- 图片主图、详情单图、白底图沿用 `ExecutionPolicy.max_quality_repairs` 作为 N，默认 2，首次生成不计入。通过审核立即交付；达到上限、无改善、预算/审核/修复异常后，从已有最终候选选优交付。
- 适用指标等权平均到 0–100。排除偏好项、不适用项与未显示的条件保留项；缺失必需要素记 0。并列选择较早候选，有评分优于无评分；所有评分缺失时仍返回较早可用最终图。
- 中间场景图、不可读取或摘要不符图片不交付。详情图仍要求三个最终目标完整；独立长图应用未扩展。
- 新交付决策 `delivery.mode=best_available` 记录候选 ID、分数、摘要、停止原因；不更改候选真实审核状态，不把 `quality.passed=false` 改成 true。全部候选与原始错误保留。
- 审核继续收到真实原图与候选，去掉推测事实描述作为外观依据，要求明确区分原图商品身份与文字创作要求。
- Web 验证交付决策、目标数量、候选身份、实际文件解码、长度及 SHA-256 后接收成果。详情组审核不通过作为警告，不阻断完整图组。
- 警告沿现有 manifest、持久成果和作品链路保存，仅显示于工作台/作品的既有任务详情。历史“尚未交付”摘要被后来的选优交付决定取代时，展示层隐藏旧摘要，原记录保留。
- 显式历史恢复只读原候选并重建原结果，不调用生成/审核模型；重复恢复稳定，安装、备份及恢复脚本可重试且保留原文件。

## 验证结果

- imageAgent 最终综合回归：**169 passed / 70.70s**。覆盖 N=0/1/2、早期候选胜出、并列、无评分、预算/修复异常、阶段图排除、损坏图、HTTP 契约、秘密投影后的摘要绑定、正常生成、候选保留、组图、人工接受兼容及恢复。
- 安装到实际 imageAgent 后新增回归：**16 passed / 9.04s**。
- Web 图片适配单测：**53 passed**，覆盖选优凭据、字节摘要、完整目标、不可读结果拒绝与警告传递。
- 前端本次关联回归：**22 passed**；TypeScript 检查、Vite 构建通过。相关 Python Ruff 与 Git whitespace 检查通过。
- 独立只读评审发现并修正评分遗漏必需要素和恢复脚本中断后不可重试两项问题；最终未发现剩余可复现 P1/P2。
- 本机图片 API、Web API ready 通过，平台 Worker 按原队列 `TEST_ONLY:local-text:20261016`、原消费组及并发 4 恢复。

## 当前故障任务恢复证据

- 平台任务 `T20261018-000010` / `b9536d1a-0c88-4099-8db1-074f28e3b641`，上游 `f7866af5-2040-4333-a161-b6f652e29834`。
- 三个最终候选为 c0001 / c0003 / c0005，综合分 **83 / 81 / 66**，选择 c0001。c0002 / c0004 是中间场景图，不参与选优。
- 选中原图 SHA-256：`ed17ee2e3cedd81d111acdbf0b984ed7c1da4060026010d06738e902c83d2f04`。
- 先在真实 run 完整副本验证，再备份并恢复原任务。原调用计数保持 **image_calls=5 / vision_calls=5**，本轮没有新增供应商调用。
- 通过原结果轮询、验证、保存、发布与结算链路成为 `SUCCEEDED / CONSUMED`。正式作品 `5a3a6ccf-4a83-4066-98ce-ec84d863ee5e`，20 积分；数据库核对一份作品、一笔 consume 流水。重复执行恢复仍各一条。
- Chrome 实际查看原任务：生成成功；作品图片正常解码 1024×1024；下载 HTTP 200、image/png、1,357,223 字节，浏览器计算摘要与选中原图一致。详情显示 c0001、83 分和真实审核疑点，旧未交付摘要不再显示。刷新后报价 200，页面无错误提示。

## 其他测试及限制

不能声称整套测试全部通过。Web 全量单元运行 **590 passed / 2 failed**，失败为 `test_display_numbers.py::test_task_projection_preserves_number_across_state_changes_and_replay` 与 `test_task_detail_contains_persisted_owned_conversation_number`。前端全量 **285 passed / 2 failed**，失败为 `user-identity-display.spec.ts` 的 `shows accounts in user lists, details and recipient options without UUID fallbacks` 与 `keeps an unknown pending grant inspectable without exposing its internal recipient`；本轮未修改这些用户管理/编号功能。

imageAgent 旧全量探索运行保留了旧规则预期失败，后因覆盖范围较大停止，不能算全套完成；相关规则断言已随本次交付语义同步并通过上述 169 项。另在原 imageAgent 未安装源码上确认 `test_repair_semantics.py::test_unverified_required_appearance_needs_evidence_before_generation` 三个参数用例原已失败（仍要求已被用户取消的事实门槛），未通过恢复旧阻断来让它们变绿。

没有为本次验证重新提交付费生成；未来供应商实际行为无法由离线测试保证。现有所有者授权、不可变原任务身份、完整交付、保存恢复和消费唯一性仍沿用原实现。

证据保留于忽略目录 `backend/.tmp/image-best-candidate/`：`final-focused-regression.log`、`web-unit-regression.log`、`recorded-task-proof.json`、`original-hashes.json`、`installed-hashes.json`、`before-install/` 和 `task-before-recovery/`。服务日志在 `.local-data/runtime/`：image-api `20261018-204049-035940`、web-api `20261018-204056-302323`、worker `20261018-204211-354485`。
