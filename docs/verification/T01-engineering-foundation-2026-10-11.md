# T01 工程基础验收

日期：2026-10-11。范围：可启动工程、配置、共享 DTO、类型生成、真实服务测试基础。启动和清理见[工程说明](../development/t01-bootstrap.md)。尚未实现业务页面、积分、生成任务或真实 Agent 接入。

主控独立验证：后端 27 项（含真实 MySQL 8.4.8 / Redis 7.4.8）通过，无 skip；ruff、前端类型检查、构建、OpenAPI 和 TypeScript 契约一致性检查通过；Vitest 1 项、desktop/mobile Playwright 各 1 项通过。真实 HTTP live/ready/mock 返回 200，测试 API 已退出。测试用户仅获测试库权限，探针表清理后为零。

独立评审发现并关闭两项问题：版本控制固定 LF，避免 Windows 检出破坏 Linux shell 和生成文件检查；单元测试隔离并恢复继承的 APP_*。修复后污染环境下 21 项单元测试和完整后端 27 项再次通过；实际 core.autocrlf=true 检出脚本和两份生成契约均保持 LF，WSL shell 语法检查通过。聚焦复核结论 Approved，无残余重要问题。

验证前后完整源码 manifest 一致。原始实现、独立验证、评审和修复证据保存在本地忽略目录 `.agent-runs/2026-10-11-implementation/`，任务 T01 / R-T01；最终 manifest 为 `2afd18df5c23f49bedbd8fc4cc107e09418b08b6e9a8700524f156c59accaccc`。

本地开发需保持前台 WSL Compose 会话。持久根检查验证配置声明与写入/fsync，不代替 T24 的实际挂载和恢复演练；Redis Streams 仅完成调度选型。未决生产能力由后续任务继续保持关闭。本记录不代表生产或首版业务验收通过。
