# T09 上游提交证据与原任务恢复验收

本阶段建立持久提交 attempt 与不可变上游 observation，按平台 Agent UUID、固定目录版本、协议、原 external/upstream ID 与输入快照核对身份。实际 worker 已接入原任务提交、查单和核查；网络调用不跨数据库事务，状态写入承接租约、fencing 与 CAS。

## 验证结果

- 最终主控后端回归：328 项通过，无跳过或警告；Ruff、OpenAPI 一致性检查通过。测试前后源码不变，配置快照为 `736a6da47f8565f3163526522df5d9c16df7d1d83ae2c475f452452ce0f19914`。
- 实现者最终定向回归：111 项通过；应用时钟正负 30 秒的两个独立进程各 9 项通过。
- 原独立评审发现的首次探测恢复问题与两轮修复均已复评；最终 Spec compliant、qualityApproved，无未解决 Critical 或 Important。
- 12 个冻结文件逐项 SHA256 和 Git index 已核对；最终评审 tree 为 `a33ada054333fd9790d3ff4fe64f24f806830b99`。
- 前端和契约构建相关 18 个文件与 T07 已验证版本一致；实际 MySQL head 为 `0011_upstream_attempts`，原任务唯一绑定约束 `(agent_id, upstream_id)` 已在实库核对。

## 恢复边界与修复

首次上游实例探测不可用且尚无 attempt 时，任务保留 SUBMITTED/QUEUED，释放租约后可重试探测。已有或未知提交不能据此获得新生成许可；历史无 attempt 的 INVESTIGATING 记录也不被自动重新分类。

可信 TEST_ONLY 非受理证明使用同实例整数 checkpoint 和覆盖序列，并重读持久原始来源。普通 NOT_FOUND 不能排除未知在途提交；每个已发出的 attempt 仍需有效持久非受理回包。同源时间形状及未来声明继续核查，数据库 UTC 负责租约和证明收件时间。

初次全量出现 311 通过、1 失败，诊断确认跨主机墙钟偏移和 MySQL JSON double 往返差异。第一轮修复后全量为 319 通过、5 失败，进一步量化确认初始 Outbox 主机时间领先数据库会延后即时派发，两份旧测试证明也使用了主机时间。最终初始 ready_at 在 INSERT 中由数据库 UTC 生成，测试正例证明使用数据库时间，未来证明仍拒绝。所有原失败、受控 RED 和修复证据保留，未以一次重跑成功替代根因修复。

两份时钟偏移诊断包装输出各有一条 anyio assertion-rewrite 警告，作为非阻断 Minor 观察保留。常规定向与主控全量输出均无该警告；如将来复用包装，可调整 pytest 初始化顺序，无需修改历史证据。

## 证据与后续

证据位于 `.agent-runs/2026-10-11-implementation/`：原实现和评审报告、`reports/T09-fix1.md`、`reports/T09-fix2.md`、两轮复评及冻结后追加记录；最终清单 `evidence/T09-fix2-freeze-manifest.json`、主控 `evidence/T09-fix2-controller-165532-summary.json`、前端闭包 `evidence/T09-fix2-frontend-closure-165609.json` 与实库约束 `evidence/T09-controller-upstream-constraint.json`。

本步只恢复受理与原任务运行状态，持久结果清单供 T10 后续归并。完整保存、发布和积分结算分别归 T11/T12；结果通知不能直接成功或消费积分。测试使用真实隔离 MySQL/Redis 与模拟 HTTP 上游，未运行三个真实业务 Agent。生产协议和政策仍按未确认门槛关闭，本验收不代表真实联调或生产通过。
