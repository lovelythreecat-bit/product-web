# 平台交付与后续验收清单

当前状态：平台代码子步已交付；完整首版及上线验收 **pending**。三核心生成 Agent 真实接入与独立桥接 **DEFERRED_BY_USER**。本次只补交付材料，不执行原 T25 大矩阵。

## 已交付代码与正式专项记录

以下链接只代表各自记录内的代码与限定验证，不能合并成整项 AC 或聚合任务 PASS。

| 交付 | 正式记录 |
| --- | --- |
| 工程、配置、契约与政策门槛 | [T01](verification/T01-engineering-foundation-2026-10-11.md)、[T02](verification/T02-policy-foundation-2026-10-11.md)、[T03 mock 适配](verification/T03-agent-contracts-2026-10-11.md) |
| 账户与积分、目录报价、上传容量、原子任务受理 | [T04](verification/T04-auth-credit-foundation-2026-10-11.md)、[T05](verification/T05-catalog-quotes-2026-10-11.md)、[T06](verification/T06-upload-storage-capacity-2026-10-11.md)、[T07](verification/T07-task-admission-2026-10-11.md) |
| Outbox 派发恢复、上游不明状态、回调轮询、成果保存、发布结算 | [T08](verification/T08-dispatch-recovery-2026-10-11.md)、[T09](verification/T09-upstream-recovery-2026-10-12.md)、[T10](verification/T10-callbacks-polling-2026-10-12.md)、[T11](verification/T11-result-persistence-2026-10-12.md)、[T12](verification/T12-publication-settlement-2026-10-12.md) |
| 人工核查、SSE、指令辅助、作品历史与生命周期 | [T13](verification/T13-investigations-2026-10-12.md)、[T14](verification/T14-sse-2026-10-12.md)、[T15](verification/T15-assist-2026-10-12.md)、[T16](verification/T16-works-history-2026-10-12.md)、[T17](verification/T17-lifecycle-2026-10-12.md) |
| 共享前端、账号积分、工作台作品 | [T18a](verification/T18a-frontend-foundation-2026-10-12.md)、[T18b](verification/T18b-auth-account-2026-10-12.md)、[T18c](verification/T18c-workspace-works-2026-10-12.md) |
| 后台接口与页面、官网内容与案例、UI 收尾 | [T19a](verification/T19a-admin-api-2026-10-12.md)、[T19b](verification/T19b-admin-pages-2026-10-12.md)、[T20a](verification/T20a-site-content-2026-10-12.md)、[T21a](verification/T21a-ui-finish-2026-10-12.md) |
| 部署配置、脱敏日志、只读监控核对与备份恢复工具代码 | [T22a](verification/T22a-operations-code-2026-10-13.md)、[运行手册](../infra/runbooks) |

依赖锁、API / 类型、迁移与启动命令见 [README](../README.md)。实际 head 为 0021_site_content；环境示例的 APP 开发库保留，测试使用 ecommerce_ai_test_t07_20261011 隔离库。

## 尚未完成

- [ ] 原 T18～T25 聚合：完整双端用户 / 后台流程、F01～08、全量集成、故障 / 并发 / 权限组合与 AC-01～30 逐案独立验收。历史专项通过范围仍以原记录为准。
- [ ] T23 真实文案 / 图片 / 视频 Agent 联调与独立桥接：DEFERRED_BY_USER；重新授权后再推进，协议继续 draft / production disabled。
- [ ] T22 / T24 实际镜像、nginx / TLS / 容器 / 网络与告警投递验证；真实数据库 / 文件一致备份恢复、迁移 trigger / definer、持续围栏、cutoff 后变更核对、RPO / RTO 演练。
- [ ] D-01～D-12 生产版本及审批 pending：Agent 能力 / 输入 / 规格 / 多结果、价格赠送与辅助、用量成本、账户恢复、异常与生命周期、存储下载、品牌案例、部署与公开说明，按[需求 D 节](电商AI创作平台-首版需求终稿-2026-10-09.md)由相应负责人确认。
- [ ] 发布负责人最终确认。无真实成果或授权证据不得公开案例；未知成本保持 unavailable；未决功能保持关闭。

[AC 追踪](verification/acceptance.csv)的 NOT_RUN 表示综合验收未执行，DEFERRED_BY_USER 表示本次明确暂缓真实 Agent 所需验证；均不等于历史代码专项失败。没有填写 PASS 或代签上线批准。本清单也不宣称本次裸启动已完成业务演示。
