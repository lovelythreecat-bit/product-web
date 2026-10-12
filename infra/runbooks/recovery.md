# 备份、隔离恢复与原任务恢复

## T22a 工具边界

以下代码路径已实现；实际导出/导入、停写、故障演练与 RPO/RTO 核验属于 T24，尚未执行。D12 的真实环境、绝对路径、频率、恢复时限和批准引用缺失时拒绝运行。脚本不停止服务、不自动获取停写权、不修改只读围栏、不清理失败现场。

### 一致备份

运维必须先在已批准目标证明所有 API、worker、cleanup、上传和后台写者静止并完成在途文件写入，同时提供同一 cutoff 的只读文件系统快照/不可变存储引用，且 MySQL `super_read_only=1`（包括停止该快照上的复制写入）。这一步必须由平台特定受控流程实施并留下证据；脚本不会根据一张 JSON 自行宣布停止成功。服务器 UUID、cutoff、冻结有效期和批准引用必须来自该流程。

备份拥有根须预先创建 `.operations-owner.json`，形如 `{"owner":"<归属UUID>","purpose":"backup"}`；设置操作员独占 ACL，目标必须是该根下不存在的新子目录，不能在 release 或 storage 内。输入的 storage 与 release 必须是独立绝对路径，路径链不允许符号链接/junction。数据库凭据由 `OPS_DATABASE_URL` 提供给 Python，客户端使用独立受保护 `DefaultsFile`；该文件只放相同账号的认证/TLS配置，host/port/user/database 由已批准 URL 明确覆盖。不要将秘密放到命令行、记录日志或提交仓库。

Proof JSON 必填：`d12_approved:true`、`approval_ref`、`writer_fence_ref`、`storage_snapshot_ref`、`writers_quiesced:true`、`storage_root`、`host`、`port`、`database`、`server_uuid`、`cutoff`、`fenced_until`（带时区 ISO8601）、`migration_head`（当前代码为 `0021_site_content`）、`release_sha`（40位）。这些是有权操作员提供的证据引用，不是应用政策批准 API。未有真实批准不得填 true 冒充批准。

在项目根执行接口（所有占位值必须替换为获批绝对路径；本步未运行）：

```powershell
& ./infra/scripts/backup.ps1 -Destination <fresh-backup-dir> -Manifest <fresh-backup-dir/manifest.json> -StorageRoot <fenced-storage-root> -ReleaseRoot <release-root> -OwnedRoot <backup-owned-root> -Owner <uuid> -Proof <proof-json> -MySqlDump <mysql-8.4-mysqldump-exe> -DefaultsFile <protected-client-file> -Python <backend-python>
```

脚本验证服务器/版本/只读围栏、全部表为 InnoDB、实际 migration head、DB 引用与磁盘摘要，运行 mysqldump 一致事务并包含触发器；复制持久根所有文件（包括未确认保存 journal/part、独立公开副本）。导出前后全树 hash 与引用清单必须一致，围栏和有效期必须仍成立。缺失 durable/published 文件拒绝；cleanup_pending/withdrawn/unavailable 的物理缺失合法，但若仍有副本必须校验 hash 并纳入清单。清单不可通过只扫磁盘替代 DB 引用核对。

成功输出 `database.sql`、`storage/`、`inventory.json`、`consistency.json` 和最后生成的 `manifest.json`；manifest 包含 cutoff、完成时间、release SHA、数据库版本/head、锁文件与 compose SHA256、数据库和全部文件的大小/hash。打印 manifest SHA256，保存到独立受控证据库。无 manifest 或退出非零都是不完整备份，不可用于恢复。备份含敏感用户数据，访问权限、加密和保留期按 D12 执行，不自动上传或删旧备份。

### 隔离恢复

目标必须是与源不同 UUID 的独立 MySQL 8.4 服务器，网络隔离，由 `OPS_RESTORE_DATABASE_URL` 指定；账号只授权本次新库及必要创建权限，不授予跨库写入/FILE 权限。库名固定为 `restore_<owner UUID去连字符>`，既有同名库一律拒绝。目标父根标记为 `{"owner":"<uuid>","purpose":"isolated-restore","network_isolated":true}`，目标目录必须不存在。隔离 proof 必填 `d12_approved:true`、`approval_ref`、`network_isolated:true`、`host`、`port`、`database`、`server_uuid`、`owner`、带时区 `expires_at`；通过基础设施受控流程真实验证网络隔离，JSON 不代替防火墙。

```powershell
& ./infra/scripts/restore.ps1 -Manifest <backup-manifest> -ManifestSha256 <independently-recorded-sha256> -Target <fresh-isolated-dir> -OwnedRoot <restore-owned-root> -Owner <uuid> -Proof <isolation-proof> -MySql <mysql-8.4-client-exe> -DefaultsFile <isolated-protected-client-file> -Python <backend-python>
```

恢复先核对独立保存的 manifest hash、数据库 SQL/文件摘要和 DB 引用，再复制清单中的文件，创建隔离标记，再创建新库并通过 mysql 导入（不自动启动服务）。随后核对 migration head 与恢复 DB 文件引用。失败保留 `.restore-incomplete.json` 和新库现场，不删除、不覆盖、不自动重试到既有目标；`restore-result.json` 才是隔离恢复结束记录，incomplete 标记保留为原始开始记录。

恢复的 storage 始终带 `.restore-isolated.json`；API 全部返回503，worker/Compose入口拒绝使用它。旧快照可能仍记 published，因此恢复绝不直接开放公开访问。必须从权威审计/存续库取得 cutoff 之后的撤回、禁用和删除记录，逐项重放经批准的业务处置并验证公开 API 拒绝状态；无法取得完整记录则持续封锁。保留原 cleanup_pending/withdrawn 事实和容量占用，不把物理复制成功当作重新授权。经过账本、文件、原任务、撤回差异核对以及 D12/T24 明确批准后，才能由独立受控流程解除隔离；本脚本不提供解锁参数。

离线摘要核对：`<backend-python> infra/scripts/verify_storage.py --root <storage> --inventory <inventory.json>`。运营账本核对：`<backend-python> infra/scripts/reconcile.py --storage-root <root> --thresholds <D12-json>`。reconcile 仅 SELECT，不自动修复账本、任务、结算或冻结。Redis 流不恢复为业务事实，原 MySQL Outbox/recovery_due 驱动后续恢复；不运行 FLUSH。

## 原任务恢复机制（T08 及后续接线）

MySQL 是任务、原始快照、积分冻结、状态事件和恢复时间的事实源；Redis Stream 只是可重复的唤醒提示。新增迁移 `0010_task_recovery` 承接 `0009_tasks_admission`，不修改已有版本。

## 运行与诊断

从 backend 目录启动 `python -m worker.main --stream <本部署专用流>`，配置 `APP_DATABASE_URL` 和 `APP_REDIS_URL`；`--once` 执行一个周期。先核实数据库 head。开发 compose 的 backend-test 使用 `ecommerce_ai_test_t07_20261011`；首次 MySQL 初始化脚本同时保留旧测试库并创建/授权此库。已有卷不会重跑初始化脚本，不能通过删除共享卷或旧库来重建测试环境。T09–T13 已接阶段处理器，真实上游协议仍未启用；`unhandled` 表示原任务保留待恢复，不能据此宣称已生成、已保存或已交付。生产相关 D 决策仍须通过后续服务门槛。

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
