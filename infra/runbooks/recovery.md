# 任务恢复操作手册草稿（T08）

MySQL 是任务、原始快照、积分冻结、状态事件和恢复时间的事实源；Redis Stream 只是可重复的唤醒提示。新增迁移 `0010_task_recovery` 承接 `0009_tasks_admission`，不修改已有版本。

## 运行与诊断

从 backend 目录启动 `python -m worker.main --stream <本部署专用流>`，配置 `APP_DATABASE_URL` 和 `APP_REDIS_URL`；`--once` 执行一个周期。先升级数据库到 head。开发 compose 的 backend-test 使用 `ecommerce_ai_test_t07_20261011`；首次 MySQL 初始化脚本同时保留旧测试库并创建/授权此库。已有卷不会重跑初始化脚本，已有库沿用主控已创建的新 schema，不能通过删除共享卷或旧库来重建测试环境。当前默认没有 T09/T10/T11/T12/T13 上游处理器，日志 `unhandled` 表示原任务保留待接入/待恢复，不能据此宣称已生成、已保存或已交付。生产相关 D 决策仍须通过后续服务门槛。

每周期扫描到期任务，重新激活 Outbox（包括已经投递和 ACK 的事件），再派发 Redis 并消费。Redis 故障不删除 MySQL 记录；数据库故障只记录固定错误码并等待下一轮。消费异常不会自动改失败或积分。停止后重新启动即可按同一个 task ID 恢复，无需建立新任务、重新冻结或手改结算。

租约采用 MySQL UTC 时间；`recover_due_tasks(now=...)` 参数只保留接口兼容，始终以数据库时间判定。租约过期后新领取使 fencing token 单调递增；旧 token 无法续租、释放或迁移状态。长期处理器应定期 `LeaseManager.renew(lease)`，并在回写事务使用 `transition_task` 校验当前租约。租约失效不能取消已经发出的外部请求，也不证明上游未受理。

只可清理本部署或本测试拥有的 Redis namespace。测试使用随机 `TEST_ONLY:<uuid>:` 前缀并显式限定该 fixture 的 task IDs；禁止 FLUSHDB、FLUSHALL、停共享服务。正式构造器不传 task_ids，扫描所有持久 due 任务；task_ids 可供受控的单任务运维修复使用。

## 按阶段接线

`TaskConsumer(..., handlers={action: callable})` 注册可信处理器。签名 `handler(context: HandlerContext) -> None`；context 含 task_id/state/state_version/agent_id/agent_version/external_submission_id/upstream_id/action/lease。处理器自行打开短事务读取快照、登记证据和提交阶段。处理器运行时调度器没有打开数据库事务或持有任务锁。

| action | 持久阶段 | 接入责任 |
| --- | --- | --- |
| prepare_submission | SUBMITTED/QUEUED，且没有上游 ID | T09 校验提交协议并先持久 attempt/SUBMITTING，再调用上游；有历史意图则先核查 |
| reconcile_submission | SUBMITTING/RUNNING，无上游 ID | T09/T10 按固定 external ID 查询原意图，不盲目 submit |
| query_original | 非保存、非终态且已有上游 ID | T10 查原 ID，不能以查单错误发起新生成 |
| save_original | SAVING/SAVE_RECOVERY | T11 仅恢复原成果、原 save job |
| investigate | INVESTIGATING 且没有上游 ID | T13 核查；期限和 NOT_FOUND 均非失败证据 |

Redis 消息只携带 event_id/task_id/state_version。消费者先核对持久 Outbox 身份，再领取任务，最后按数据库的当前阶段选处理器；旧消息不会把 SAVING 回退为 RUNNING，也不会把 SUBMITTING 当成新的生成任务。缺 handler、ACK 后崩溃、流丢失均由 recovery_due_at 与有效租约驱动补调度。

## 状态和可信证据

`transition_task(session, task_id, expected_version, event, evidence) -> TransitionReceipt` 参与调用方事务，不提交。event 为目标 TaskState；evidence 为 `TransitionEvidence(lease, reference=None)`。迁移更新任务、版本、append-only TaskStateEvent、DurableEvent 与下一阶段 Outbox，同事务回滚。服务先 user 后 task；需要 credit/capacity 等锁的发布服务必须按 user/credit → capacity → task → reservation 顺序预先取得锁，不能持 task 后首次取前置资源锁。

可信服务在该 Session 上安装 `session.info["transition_verifiers"] = TransitionVerifiers({...})`。验证器签名 `validator(session, locked_task, target_state, reference) -> VerifiedTransition`，在同事务重新读取其持久证据，不得外部 I/O。返回结构必须绑定 task_id、agent_id、agent_version、external_submission_id、kind、reference、protocol_version，以及已有的 upstream_id。reference 必须是可审计的短标识而非用户正文或令牌。此 registry 是服务器内部依赖，禁止由请求体配置。

T09 注册 accepted/safe_retry；T10 注册 original_result/definite_failure；T11 注册 original_save；T12 注册 publication；T13 注册 manual_close。safe_retry 还必须携带 `SafeRetryEvidence(protocol_version, kind, reference, verified_by, verified_at)`，kind 只接受 reliable_idempotency/proven_not_accepted，证据时间不能在数据库当前时间之后；发现原 upstream ID 时必须查原。safe_retry 必须核实 D-01 可靠幂等或可靠未受理协议，普通 404/暂未查到/租约过期无效。有 upstream ID 禁止回到 QUEUED/SUBMITTING。可信接受/成果证据可在同一 CAS 中绑定原 upstream ID，已有身份不能替换。

publication 必须由 T12 读取完整持久成果及 message/work 的原子发布证据；状态机额外要求任务 CONSUMED 与原 CreditReservation consumed 同事务成立。失败/人工关闭需要可信失败/政策证据以及原冻结已由结算服务 RELEASED。布尔值不能充当证据；T08 不直接消费或释放积分。终态拒绝所有状态迁移；T10/T13 后续负责记录迟到或冲突业务审计。

## 崩溃点

- 受理提交后 Redis 写失败：Outbox pending 保留，attempts 增加，重试同 event/task。
- Redis 写成功、标记 dispatched 前崩溃：允许重复消息；消费重新核对持久阶段。
- dispatched 后流删除或 ACK 后崩溃：扫描持久 due 与过期租约，重置原恢复事件派发标记。
- handler 崩溃：保留阶段与原快照；租约到期后按原阶段恢复。
- 状态和事件事务提交前崩溃：所有迁移写入一起回滚；提交后则恢复下一阶段。
- 已有上游 ID、保存失败、期限届满：查原/恢复原/核查；不把未知当失败，不新建意图。

本步验证真实 MySQL 8.4 和 Redis 7.4 的调度故障与数据库并发；尚未运行真实 Agent、真实生成、文件持久发布或结算交付，后续阶段接入和生产验收另行完成。
