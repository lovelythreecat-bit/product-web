# 最近任务删除与独立再生成验证

日期：2026-10-18。用户确认删除含义与独立任务方案后实施；范围仅创作工作台相关行为。

## 最终行为

- 桌面最近任务逐项提供删除图标，手机提供「删除所选任务」。沿用公共删除确认弹窗，说明对象、创建时间，以及作品、积分和审计记录保留。取消不修改历史，失败保留任务并可重试。
- `DELETE /api/v1/tasks/{id}` 校验登录、CSRF 与所有者，幂等记录 `history_deleted_at`。删除持久化移出任务列表，不删除执行身份、快照、素材引用、作品和积分记录，不终止任务或自动退款。正在执行的原任务仍能完成、正常结算。
- 删除当前任务后转到剩余任务，无剩余时返回工作台；本地刷新不会重新加入刚删除的项。已删除任务仍可作为原分页锚点，锚点继续受所有者和会话限制。
- 基于已有任务再生成时，将当前可编辑的商品、素材、参数与指令深复制到独立会话草稿，然后展示当前费用确认。确认后创建新的提交标识和任务；取消收费确认保留新草稿，不提交生成。原任务输入、状态和产物不变。无 `?task=` 的已有会话同样创建独立草稿。
- 复制草稿不携带原确认或待确认提交。原请求结果不明时继续按原提交标识恢复，不因本次修改创建替代请求。

## 验证结果

| 检查 | 结果 |
| --- | --- |
| 前端相关单测：任务列表、任务草稿、提交恢复、任务流、工作台入口 | 60 项通过 |
| MySQL/Redis 隔离集成：任务历史、作品、删除权限、CSRF、幂等、执行延续、分页游标 | 12 项通过 |
| Edge 桌面 1440×1000、手机 390×844：新增流程及原工作台交互 | 4 项通过 |
| 视觉复核后再次验证新增桌面／手机流程 | 2 项通过；桌面删除图标与任务时间无重叠 |
| TypeScript、正式构建、OpenAPI 与生成类型一致性、相关 Python lint | 通过 |
| Impeccable 机械检查 | 未报告问题 |
| 独立代码审查及修正复核 | 分页游标、默认恢复入口两项问题已复现并修正；复核未发现新增 P1/P2 |

测试先观察到缺失功能失败：前端缺少删除入口、再生成仍停留原会话；后端 DELETE 返回 405。独立审查发现的分页游标与默认恢复入口也先补失败测试，再修正。

浏览器测试使用受控 HTTP 数据，不调用真实模型、不删除真实用户任务、不消耗真实积分。隔离集成仅连接项目现行 `ecommerce_ai_test_t07_20261011` 与 Redis 15。

## 全量检查发现的既有测试问题

- 前端完整单测运行：279 项通过、2 项失败。`user-identity-display.spec.ts` 的 `shows accounts in user lists, details and recipient options without UUID fallbacks`、`keeps an unknown pending grant inspectable without exposing its internal recipient` 仍模拟旧后台接口，而用户管理读取现有独立接口，出现网络失败。未扩大本轮范围修改后台功能或这些夹具。
- 后端单测与历史集成合并运行：595 项通过、2 项失败。`test_display_numbers.py` 的 `test_task_projection_preserves_number_across_state_changes_and_replay`、`test_task_detail_contains_persisted_owned_conversation_number` 夹具缺少现有必需的 `created_at`／`updated_at`。这两项投影与日期契约不是本轮修改内容。
- 初次沙箱运行的临时目录、回环网络权限问题已通过工作区临时目录和获准的本机测试运行解决，不将环境错误计为功能通过。

## 本机启用

已将本机数据库从 `0031_remove_storage_limits` 升至 `0032_task_history_deletion`，迁移前后均为 18 条任务；仅新增可空删除时间字段。Web API 已重载并在隐藏后台运行，复用原 Worker 与 Agent。只读检查 `/api/v1/health/ready` 返回 `ready=true`，运行中的 OpenAPI 包含 `delete_task_history`。

截图：[桌面任务列表](screenshots/task-history-actions-desktop.png)、[手机任务列表](screenshots/task-history-actions-mobile.png)、[桌面删除确认](screenshots/task-history-delete-desktop.png)、[手机删除确认](screenshots/task-history-delete-mobile.png)。

本记录证明本次局部实现与本机启用，不代表生产发布或真实模型全业务验收。
