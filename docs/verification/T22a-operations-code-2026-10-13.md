# T22a 运行工具代码交付

依原T22/T22a brief与用户代码优先要求完成 staging Compose/D12 preflight、独立持久根、nginx权限转发与禁缓存、脱敏HTTP/任务日志、监控只读投影、smoke/核对/存储验证、PowerShell备份恢复入口及Python实际 mysqldump/mysql 路径、四手册。无迁移，实际head0021。

备份要求同cutoff停写/存储围栏与D12证明，检查MySQL8.4 super_read_only/server UUID/InnoDB/head及文件摘要，完成manifest最后写入。恢复只允许不同服务器UUID、restore_<owner UUID>新库与归属新目录；摘要前后校验，失败保留隔离现场。恢复marker封锁API/worker/部署入口，cutoff后撤回/停用/删除未核对不得解封。公开副本及cleanup_pending纳入inventory；reconcile没有修账/任务/冻结写入，未知成本unavailable/null。

已执行：7个离线检查PASS/1.17s，SQLite时间函数适配仅用于离线聚合检查；限定Ruff PASS；两个PowerShell脚本AST无错；既有Compose插件 config --quiet静态通过。未使用真实凭据、未连接守护服务。主Docker compose首次exit125保留，直接既有插件解析成功，没有修Docker。

主控冻结Ruff/OpenAPI/diff均exit0、source_unchanged=true，源码快照 `a28f86bd420c13516e8fa1be0b551e5698d4d9517bf02f95f219792c0743a01a`，评审产品树 `be085b6395972857f2e5caf6a86afa884544db9e`。独立限定Spec/Quality PASS、C0/I0/M0，21文件SHA吻合。R-T22a/T22a接受revision242/243，前端未变不重复构建。

证据在 `.agent-runs/2026-10-11-implementation/`：T22a-86049947实施报告、R-T22a-f3ceab8d评审报告，evidence/T22a-86049947下 offline-pytest/Ruff/powershell-static/compose-static-direct/frozen-sha256，T22a-controller-summary和对应静态日志。受控操作员JSON证明仍须真实审批/基础设施支撑，不代替外部批准。

未验：真实DB导出导入/trigger/definer、实际备份恢复、D12审批/持续围栏、文件系统断电/fsync/ACL/并发路径、镜像构建/nginx -t/容器/TLS/网络隔离/公网、告警投递与RPO/RTO、cutoff后变更重放、真实Agent及生产。没有停共享服务、清历史、部署或恢复操作。原T22/T24聚合待验，本记录只接受工具代码。

用户另已确认独立桥接设计；随本次本地提交保存对应spec/plan文档，未在本T22a评审或生产批准范围内。下一步T23a准备候选服务，原T23真实联调仍独立待验。
