# T10 回调与轮询验收

本阶段在实际 API 注册原始字节回调入口，并将轮询和回调接入同一持久归并流程。回调验签后只持久接收，worker 持有效数据库租约处理；MySQL 事件与不可变处理决定承担防重放和内容冲突事实，适配器内存提示不代替持久判定。

## 验证

- 主控完整后端回归365项通过，无跳过或警告；Ruff、OpenAPI一致性检查通过。
- 主控契约、类型检查和前端构建均通过，两套验证前后源码一致，配置快照均为 `37c1f664ad5c4072eadbe66aa215b6d67d29b090154c27d02e314df7c5bdeab4`。
- T10专项37项通过，覆盖签名/协议/时间/身份、持久重复与冲突、乱序/终态迟到、已有观察后查询失败、实际worker接线和旧fencing。
- 独立评审 Spec PASS、qualityApproved，Critical/Important/Minor均为0；14文件实际SHA256及index与评审tree `fc1fb0cb5590c0755ebd526d7260349b7807b256` 一致。
- 实际MySQL增量迁移 `0012_agent_events` 承接0011，未修改历史迁移。无Cookie/Origin的有效签名回调已通过实际应用入口验证。

## 行为与交接

公开 `POST /api/v1/agent-callbacks/{agent_id}/{version}` 只接受原字节并按固定目录/协议绑定平台与wire身份，拒绝调用方声称已验证的字段。不同原字节重用eventID、同任务/序列内容不一致均保留冲突；过时或终态迟到收据不能再次授权保存。

正常恢复通过 `UpstreamService.poll_original_task`，先使用持久观察与待处理收据再查原任务。查询失败或普通NOT_FOUND不重新提交生成；已收获原成果后新查询不可用不会丢失恢复路线。内部 `OriginalResult` 带收据引用、固定任务/Agent/协议/external/upstream身份与快照摘要，供T11重读验证后保存。失败只形成待处理的持久证明，仍保留冻结，T12满足原子结算要求后才能终态。

中间失败证据保留，包括wire status覆盖验证结果、交接缺身份和冲突收据被复用为保存证明的RED；修复后37专项和主控365完整回归均通过。旧T09路由测试允许异步批次内RUNNING/SAVING，T10另有实际worker测试明确要求SAVING。

## 证据与限制

运行目录 `.agent-runs/2026-10-11-implementation/` 保存实现与独立评审报告、14文件冻结清单、`evidence/T10-controller-172333-summary.json`、`evidence/T10-contracts-controller-172335-summary.json` 及全部原始失败/通过输出。

当前只验证TEST_ONLY mock-v1：固定序列1/2与单个original-1成果。目录可按D-04发布多成果规格不代表当前worker能交付；T11/T12必须扩展模拟协议和固定清单/规格/政策校验，或在受理边界准确关闭不可交付规格后再完成多成果验收。真实协议、生产签名与轮换、三业务Agent接入仍归T23；本步不运行真实生成，不表示文件持久交付、作品发布或积分结算通过。
