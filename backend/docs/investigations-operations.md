# 核查与人工处置操作手册（T13）

本模块使用 MySQL 权威状态。生产 D-08 仍未确认；本次没有确认任何生产政策。
`contracts/fixtures/policies/TEST_ONLY-investigations.json` 是严格 schema 的 mock 样本，UUID 必须替换成隔离测试数据库中真实 active admin；该样本不授权生产。

## 开启与责任

现有 Worker 每次 tick 在调度前执行有界扫描（最多1000个任务，后续 tick 按游标续扫）。任务固定快照中的精确 D-08 若含有效 `investigations-v1`，自动建立负责人、首个异常状态开始计算的期限、待办和系统分派审计。负责人无效、政策缺失或尚未确认则写入 UNASSIGNED/POLICY_BLOCKED 告警；不会释放或消费积分。

运维必须把 `operations:investigations` 接入实际值班责任路径，定期查看管理员告警 API；服务不主动发送外部消息。政策 `escalation_ref` 指向已审定的责任路径。到期写 OVERDUE，原冻结保持不变。停用或降权的负责人会触发 UNASSIGNED；有权限的管理员用 assign 移交，不能靠更换负责人延长期限。

## API 工作流

所有写操作必须携带真实登录 Secure session cookie、同源 Origin、`X-Requested-With: platform` 以及与 cookie/session 绑定的 `X-CSRF-Token`。服务在处置事务中重查账号、session、auth_version、数据库 admin role；此外 actor UUID 必须在精确政策的 authorized_actor_ids 中，动作必须在 actions 中。正文只接收精确 policy_version，不能提交政策 JSON。

1. `GET /api/v1/admin/investigations`：按创建时间倒序获取未完成待办，使用 `owner`、`cursor`、`limit` 分页。
2. `GET /api/v1/admin/investigation-alerts`：使用 cursor/limit 遍历持久告警（每页最多100条；历史告警不删除；按 task_id 查当前待办确认是否仍需动作）。
3. 缺少记录时，`POST /api/v1/admin/tasks/{id}/investigations`，发送 `owner`、`policy_version`、非私有 `evidence` 引用。只能对 INVESTIGATING/SAVE_RECOVERY 建立核查；不更换原任务、快照或冻结。请求明确选择并审计的政策版本必须通过数据库门禁。
4. `POST /api/v1/admin/investigations/{task_id}/assign`，加 `expected_version`、`reason`；新旧政策均需授予该管理员权限，新责任人必须匹配新政策且仍为 active admin。审计记录原/新责任与政策，期限保持不变。
5. `POST /api/v1/admin/tasks/{id}/resolutions`，发送 `action`、`reason`、`expected_version`、`policy_version` 和 `{kind, reference}` evidence。409 时重新读当前任务/核查状态，不直接重试旧版本。

- `resume_original`：同事务登记请求和 outbox；Worker 调用原 T10 poll/T11 save/T12 publish。返回 recovery_scheduled 仅表示可靠调度，未表示成功。沿用原 external_submission_id、upstream_id、固定快照、冻结；普通 NOT_FOUND、超时或旧 lease 均不授权重新生成。完整成果恢复完成时，核查与终态/唯一结算一起提交。
- `confirm_failure`：evidence.kind=upstream_failure，reference 必须是该原任务持久 FAILURE_PENDING 的真实事件。服务在同事务调用 CallbackService.verify_definite_failure，再调用共同 release_credits；任意字符串不能当失败证据。
- `manual_close`：evidence.kind=review。当前唯一实现的政策语义为 operator_review：已授权操作人以明确理由和证据引用作出人工释放决定，持久 Resolution 是可信证明；期限不是失败证据。唯一释放后进入 MANUALLY_CLOSED，不表示上游失败。全部容量预留保留，部分 File/blob/journal 不被清理。短事务重读原 manifest 下全部 ResultSaveItem 和该预留下 File 的固定 file_id/version，将每个身份的最大声明/实际字节求和；同一身份不重复计数，尚无 File 的在途/journal 身份也纳入。预留若不足则同事务补足 pool/account/reservation；容量不足返回409且积分、CAS、核查和审计全部回滚。该步骤不查询磁盘或下载，固定保存身份已经由T11在物理I/O前提交。T17/T22 必须按确认 D-09/D-10 核算与安全回收，不能把积分释放解释为磁盘空间已释放。
- `settle`：evidence.kind=durable_delivery。先校验权限，然后在锁外调用原成果物理保存/重验，回到短事务重验权限与版本；T12 完整 durable 证明、作品/最终消息、容量核算、扣款和核查审计共同提交。请求中的引用不是交付证明；实际 manifest_id 由可信保存服务产生并记录。无成果返回409，不能人工补扣。

停用任务所有者需要其固定快照的精确 D-09 account_disable 门禁；缺失则拒绝处置并保留冻结，不绕过停用政策。

## 迟到成果与用户原因

T10先验证签名及绑定身份并登记 TERMINAL_LATE/冲突。扫描把该事件引用登记为 LATE_RESULT；本 schema 只实现明确 `late_delivery=quarantine`：保留原通知/冲突供核查，不自动下载、发布、逆转终态、补扣或创建新收费任务。其他迟到交付方案必须扩展 schema 和可信实现后再确认政策，不把未知配置降级为默认交付。

本人 `GET /api/v1/tasks/{task_id}/investigation` 只能看到状态、期限、处置原因。管理员默认诊断没有用户输入、成果正文、下载地址或秘密。reason 是会展示给用户的说明，请只填必要处置事实；evidence 应是可追溯引用。

人工处置及原任务自动完成时，同一事务同步核查的 user_reason 与任务的 investigation_reason；已有任务详情、任务列表、对话任务列表会显示最新说明。替换前的原因保存在内部审计 previous_investigation_reason，原始事件和证据引用保留，不把内部证据加入用户响应。核查期限 deadline_at 与告警 created_at 均把数据库 UTC 时间明确输出为带 Z 的 UTC 日期，客户端按本地时区显示。

## 故障与核验

MySQL 提交结果不确定时先查 generation_tasks、investigations、investigation_resolutions 及唯一 `credit_ledger.operation_key=settle:<task_id>`；不要重复手工改账。result publisher 的 published(task_id) 可验证成功提交，不重新下载或生成。已消费/已释放竞争只能有一条结算流水。写审计或CAS失败导致该处置事务全部回滚。

人工保存可能在最终CAS失败前已留下可恢复文件，仍由容量预留和原 manifest/journal 保护。不要删除或重置预留；重新读取状态后交原任务恢复。跨账户锁序为排序后的 user集合→实时session→credits→pool/account→task→reservations→investigation。外部HTTP/下载不在该锁事务内。
