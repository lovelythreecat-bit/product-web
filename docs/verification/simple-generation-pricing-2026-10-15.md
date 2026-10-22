# 按创作类型计价实施验证

日期：2026-10-15。用户要求：删除工作台生成规格和后台「规格与价格」，增加仅含文本价格、图片价格、视频价格的参数配置页面。实施与契约以 [本轮设计说明](../superpowers/specs/2026-10-15-simple-generation-pricing.md) 为准。

## 已实施

- 工作台取消规格请求、规格必填校验、规格选择和生成设置；报价使用手选 Agent，按 copy/image/video 读取对应价格。费用确认保持。商品资料、固定底部操作和既有待核对原请求恢复保持。
- 后台「参数配置」沿用暖色页面、编辑抽屉、保存取消；三业务字段均允许空值及 0，前后端严格限制安全整数。旧规格/价格页面与孤立 SpecForm 组件删除；旧页面地址重定向参数配置，旧公开规格及后台规格/价格 API 移除。
- 数据库按 mode 保存不可变价格版本及可锁定 head；后台保存具备管理员、CSRF、CAS 和修改审计。同事务持有价格读取锁至受理结束。改价后新提交拒绝旧报价，已受理同一原意图先幂等重放，不再冻结。
- 新任务内部 single envelope 由代码维护，不要求管理员建立规格或 result_specs。真实文本与 TEST_ONLY mock 的完成规则验证身份、协议、原快照、固定单结果及 MIME；原有 manifest、内容、容量、存储和结算校验保留。历史任务走历史规则和原快照。
- AI 辅助、历史作品再次创作、报价失效恢复、目录/受理/文本/作品共享测试 fixture 与浏览器 harness 同步新契约。
- 新增迁移 0026，仅新增两表、三环境空 head 和不可变触发器；没有预填费用或迁移旧费用。实施 agent 未执行迁移、未执行任何 Git 命令。开发库升级由主 agent 独立处理，状态见最终交付记录。

## 实施 agent 的定向检查

| 检查 | 命令摘要与结果 |
| --- | --- |
| 后端单测与 API | `.venv/Scripts/python.exe -m pytest tests/unit/test_generation_parameters.py tests/unit/test_text_default_model.py tests/unit/test_text_agent.py -q`：47 passed。覆盖三价格整数/null/0、保存重读、冲突、管理员/CSRF、按类型报价、报价失效、旧意图原价重放、新文本单结果保存规则无需规格。 |
| 前端直接相关单测 | `node node_modules/vitest/vitest.mjs run tests/unit/generation-parameters.spec.ts tests/unit/workspace-remediation.spec.ts tests/unit/workspace-submission-recovery.spec.ts tests/unit/workspace-drafts.spec.ts tests/unit/admin-remediation.spec.ts tests/unit/task-card-retry.spec.ts`：6 文件、33 passed。 |
| 前端类型 | `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit`：exit 0。 |
| 生产包 | `node node_modules/vite/bin/vite.js build`：exit 0，147 modules。 |
| 代码规范 | 本轮后端、迁移及直接受影响 fixture 的 Ruff：All checks passed。 |
| 契约 | `backend/scripts/export_openapi.py --check` 与 `node frontend/scripts/contracts.mjs --check`：exit 0。 |
| 真实数据库集成 | 主 agent 运行 catalog_quotes/task_admission/prompt_assist/text_admission/works_history 五文件：**101 passed，130.65s**。使用 `infra/env.example` 中受 fixture 白名单保护的 `ecommerce_test` 隔离测试库和 Redis DB15，包含迁移、真实锁、改价、受理、辅助及作品来源验证。没有使用开发库或生产库运行这些测试。 |

后端 TestClient 在沙箱内阻塞，前端 Vitest 临时目录重命名/路径解析受沙箱限制，上述单测、类型和构建在获准的沙箱外工具环境执行。未把这些环境问题计作产品通过或失败。

主 agent 独立浏览器验收已报告桌面 1440×1000 与手机 390×844 通过：三字段、抽屉取消、0 价格保存重读、工作台按 Agent 报价、不再请求规格、完整长商品资料、桌面固定操作和无横向溢出/JS 错误。该验证使用 mock API；截图位于 `frontend/.cache/simple-pricing-verification/`，不代表真实文本/图片/视频端到端生成已启用。

## 本地开发环境实际落地

- 主 agent 已核对运行模式为 mock、数据库主机 `127.0.0.1`、库名 `ecommerce_ai_dev`，应用 `0026_generation_parameters`，数据库版本由 `0025_text_default_model` 升至 `0026_generation_parameters`。
- 升级前后逐项核对 `users`、`generation_tasks`、`credit_ledger`、`agent_versions`、`generation_specs`、`price_versions` 六表行数一致；没有删除或重写历史记录。新价格版本数为 0，mock/staging/production 三个 head 均为空，没有预填费用。
- 按 18000 监听端口及 uvicorn 应用命令身份核对，仅重启本项目本地 API，保留数据库与现有登录会话。启动日志位于 `.local-data/api-generation-parameters.stdout.log` 和 `.local-data/api-generation-parameters.stderr.log`。
- 经现有 Vite 代理实测 `/api/v1/health/ready` 返回 200，`ready=true`，database/storage 检查均为 true；未登录请求 `/api/v1/admin/parameter-config` 返回 401，确认接口已加载并保留身份保护。
- 本地管理员可打开 `/admin/parameters` 填写三类价格。现场未提交真实生成任务、未填写价格、未补造生成政策或可信容量配置。

## 运行边界

其他环境部署必须先升级 0026，再填写所需价格；本机开发库已完成升级。新生成所需可信容量按 Agent UUID/版本显式配置并通过原 D-10；不回退旧规格估算、不提供默认费用或 0 容量。文本仍使用当前后台服务连接与默认模型，图片/视频未接入事实不变；当前是否可生成还取决于模型、服务权限、生成开放与容量等原门槛。没有生产发布、真实业务验收或新增图片/视频接入。
