# T08 派发、租约与恢复验收

本阶段承接 T07 的任务受理，实现 Outbox 派发、Redis Streams 消费、数据库租约与 fencing、CAS 状态迁移，以及数据库周期恢复扫描。即使消息已 ACK 或 Stream 丢失，恢复仍以 MySQL 持久状态为依据。缺少后续处理器时保留任务和冻结，不生成虚假终态。

## 验证结果

- 实现者定向状态机与恢复验证：45 项通过；业务 RED 和安全重试 RED 证据保留。
- 主控最终后端回归：284 项通过，无跳过；Ruff、OpenAPI 一致性检查通过。测试前后源码不变，配置源码快照为 `3516932255c4b70e6021eab72d94a38705a4650d78f3c556fda61cf51df9b150`。
- 前端、契约及构建相关的 18 个文件与 T07 已验证版本一致，沿用 T07 的契约、类型检查和构建证据。
- 独立原 T08 评审和额外两文件修复评审均为 Spec PASS、qualityApproved，未发现 Critical 或 Important 问题。
- 官方 Compose 测试入口选择新隔离库 `ecommerce_ai_test_t07_20261011`；保留旧库及历史记录。

## 模拟 HTTP 关闭竞态修复

初次全量回归出现 279 通过、1 失败，源于已有模拟服务器拒绝超大请求后直接关闭连接，Windows 客户端未读到已写出的 413 JSON。原失败证据保留；原源码偶发通过不作为修复依据。

受控分段请求稳定复现 WinError10053 和零响应字节；对照实验排空相同请求尾部后获得完整响应。修复先 flush 和半关闭响应方向，再按最多 128 KiB、绝对 250 ms 排空在途输入。稳定 RED 为 2 失败、1 通过；修复后模拟契约 34 项通过，最终全量 284 项通过。持续恶意发送超过预算仍可强制关闭。

## 证据与后续边界

运行证据位于 `.agent-runs/2026-10-11-implementation/`：原冻结清单 `evidence/T08-ebaf34f4-freeze.json`、修复清单 `evidence/T08-mock-fix1-freeze.json`、最终主控记录 `evidence/T08-mock-fix1-controller-155032-summary.json`、前端闭包记录 `evidence/T08-mock-fix1-frontend-closure-155112.json`，以及原评审报告和 `reports/R-T08-mock-fix1.md`。所有原失败、根因对照、RED/GREEN 记录均保留。

本阶段验证使用真实隔离 MySQL/Redis 和 TEST_ONLY 模拟环境。T09 上游提交证据、T10 结果接收、T11 保存、T12 发布结算及 T13 人工核查尚待实施；当前 worker 不以缺失处理器推断失败。未运行三个真实业务 Agent，未确认生产政策仍关闭。本阶段不代表真实联调或生产验收通过。
