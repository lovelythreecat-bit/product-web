# 文本 Agent 推理强度与警告传递

日期：2026-10-18。依据：用户明确要求「补齐推理强度配置和警告传递」。对照本机 `F:/Work/电商/textAgent` 的现行源码；本轮只修改 web 项目。

## 实现

- 后台文本模型抽屉新增推理强度。默认「沿用模型默认」发送 null；none/minimal/low/medium/high/xhigh/max 原值转发，none 不等于 null。支持新增、修改、列表及单模型回读，未知档位在 web 受理前拒绝。
- 模型参数与模型 Key 仍唯一归 textAgent。web 不新增模型参数数据库副本；服务 Key、默认模型选择、版本冲突、只写密钥规则保持原契约。
- 提交响应及原记录查询均读取 `warnings`，随已验证的 ResultManifest、持久化清单和最终消息保存，作品列表与详情通过 WorkView 返回。警告参与交付与发布一致性验证，恢复不额外发起生成。
- 按用户后续要求，工作台和我的作品的「待核实提示」统一放入各自任务详情抽屉；共用 ResultViewer 的正文、作品列表与预览均不展示。警告按纯文本渲染，HTML 不执行；复制、正文哈希及 TXT 下载仍只对应上游原正文。下表为首次传递能力验证，最新展示位置验证见文末。
- 空警告不进入清单及最终消息的序列化，保留历史 receipt、manifest 和 message 的原形状。旧作品通过接口返回空警告数组，不补造、不重新生成。
- 使用现有 JSON 持久化字段，无新增数据库迁移。运行中的 API 与 Worker 需要重新加载本次代码；本轮未改当前服务连接、默认模型、真实模型参数或运行进程。

## 验证

| 检查 | 结果 |
| --- | --- |
| 文本后端专项 | 91 passed，覆盖配置透传、null 清空、提交与原记录警告恢复、历史序列化、发布正文分离 |
| 新增前端专项 | 7 passed，覆盖配置保存回读、none 与默认区分、警告展示及预览、纯文本渲染、复制正文不混入警告 |
| 隔离 HTTP / MySQL / Redis 文本管线 | 14 passed，legacy 与 database 两种路由均覆盖实际保存、恢复、作品读取、发布校验及一次结算 |
| 桌面与手机浏览器 | 4 passed；警告刷新和预览 2 项通过，推理强度修正可访问名称后重跑 2 项通过 |
| TypeScript / Vite 构建 | 通过 |
| OpenAPI / TS 契约 | 已重新生成，校验通过 |
| 本次后端文件 Ruff | 通过 |
| 独立只读代码评审 | 本轮限定范围未发现具体缺陷 |

隔离服务测试仅连接 `ecommerce_test` / `ecommerce_ai_test_t07_20261011` 和 Redis 15，模型响应由受控本地 HTTP 服务提供，没有调用真实模型。

### 全量回归中的未通过项

后端默认测试：633 passed、478 skipped、3 failed。未提供隔离服务环境的集成测试按项目规则跳过；另有上表 14 项明确配置隔离服务后通过。三个失败位于本轮未修改的测试及任务时间字段路径：

- `test_display_numbers.py::test_task_projection_preserves_number_across_state_changes_and_replay`：SimpleNamespace 任务夹具缺少 created_at。
- `test_display_numbers.py::test_task_detail_contains_persisted_owned_conversation_number`：任务夹具缺少 created_at、updated_at。
- `test_generation_parameters.py::test_original_admitted_intent_replays_without_using_new_prices`：幂等回放夹具缺少 created_at、updated_at。

前端全量：271 passed、6 failed。`runtime-lifecycle.spec.ts` 的 4 项失败涉及沙箱本地 socket 连接权限，沙箱外定向复跑全部通过。剩余两项：

- `user-identity-display.spec.ts::shows accounts in user lists, details and recipient options without UUID fallbacks`
- `user-identity-display.spec.ts::keeps an unknown pending grant inspectable without exposing its internal recipient`

这两项在沙箱外仍失败：测试 Mock 的是 `api/admin`，现行 UsersView 使用 `api/adminUsers`，因此出现网络失败而非注入的用户数据。本轮未修改上述文件或账户流程。定向复跑四个前端文件的结果为 16 passed、2 failed，本次文本专项均通过。

原始日志：`backend/.local-data/text-alignment-backend-suite.log`、`frontend/.tmp/text-alignment-suite.log`、`frontend/.tmp/text-alignment-recheck.log`。没有把全量回归标记为全绿。

### 截图

测试接口注入的预览，不代表真实模型生成或生产验收。

- [桌面推理强度](screenshots/text-reasoning-2026-10-18-desktop.png)
- [手机推理强度](screenshots/text-reasoning-2026-10-18-mobile.png)
- [桌面文案警告](screenshots/text-warnings-2026-10-18-desktop.png)
- [手机文案警告](screenshots/text-warnings-2026-10-18-mobile.png)

本轮保留工作区其他既有修改，没有提交、发布、真实收费生成或历史数据回填。

## 同日追加：待核实提示收进任务详情

依据用户最新要求，创作工作台和我的作品均仅在「任务详情」抽屉显示已保存警告；正文区域、作品列表和作品预览不再显示。工作台汇总当前任务已读取的文案作品警告，作品页读取所选作品详情中的警告；继续共用 `TextWarnings` 纯文本展示。没有警告时不显示提示区，警告数据及复制、下载原文的行为不变。

验证：相关组件测试 24 passed；桌面 1440×1000、手机 390×844 浏览器专项 2 passed，覆盖刷新后详情仍可查看提示、页面与预览不展示、作品页详情可查看，以及无横向溢出、无页面脚本错误、未提交生成任务。TypeScript 检查及 Vite 生产构建通过。浏览器专项使用合成接口数据，在沙箱外运行；测试曾因关闭按钮有两个同名入口而失败，改为定位底部关闭按钮后重跑通过。

已查看[桌面任务详情截图](screenshots/task-detail-warnings-2026-10-18-desktop.png)和[手机任务详情截图](screenshots/task-detail-warnings-2026-10-18-mobile.png)，提示位于抽屉内且文字完整；上方首次实现的正文旁及预览警告截图仅保留为历史记录。
