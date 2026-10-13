# 2026-10-13 平台交付范围

用户最新明确：三核心生成文案 / 图片 / 视频 Agent 仍调试，本次只预留，不做真实接入或独立桥接；代码优先，收紧评审与测试。此指令覆盖此前已批准的 [10-12 桥接 spec](superpowers/specs/2026-10-12-agent-bridge-preparation.md) 与 [桥接 plan](superpowers/plans/2026-10-12-agent-bridge-preparation.md) 的本次执行安排。历史文件保留为历史依据，本次桥接暂缓，状态 DEFERRED_BY_USER，不作为代码缺陷或通过验收。

平台既有 AgentAdapter、mock、任务 / 账本 / 恢复 / 作品接口保留，三个协议仍 draft、production_enabled:false。未来真实接入仍须按需求满足对应 D 和真实联调，不因预留接口而自动启用。

本次为[原开发计划 T25](superpowers/plans/2026-10-09-ecommerce-ai-platform.md)的交付文档及 AC 追踪子步：仅增加根 README、范围说明、交付清单、acceptance.csv，更新前端说明的迁移 head / 边界链接，以及环境示例隔离测试库。没有新增桥接 / 业务代码、迁移、启动器或测试，没有恢复已归档的不完整草稿。

历史代码交付以 [交付清单](release-checklist.md) 关联的正式专项记录为准，原 T18～T25 聚合仍 pending。AC CSV 是综合验收状态登记；历史专项证据单独列出，不能冒充 AC 逐案总验收。生产 D-01～D-12 保持 pending，不代签批准。

本次最小验证仅查 CSV 格式与连续唯一的 30 个 ID、引用存在、迁移 head / 环境示例一致性及 git diff --check。未执行后端 / 前端全套、浏览器、长矩阵、真实 Agent、备份恢复、staging 或生产操作。
