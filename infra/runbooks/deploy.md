# 隔离预发布部署

本文件是待 D-12 批准的工具流程，云厂商、持久路径、RPO/RTO、备份频率、监控阈值、公开入口和协议均无生产默认值。T22a 只交付代码；T24 才执行明确授权的隔离演练。生产整体仍关闭。真实 Agent 接线未完成，启动 staging 不代表可真实生成。

## 布局与启动前提

以实际批准的绝对路径提供 `RELEASE_ROOT` 与 `PERSISTENT_ROOT`，两者不得相等或互为子目录。持久根下由运维创建并设置最小权限的 `mysql/`、`redis/`、`storage/`，发布目录只含代码与前端 dist。Compose 不自动创建宿主路径；没有匿名数据卷，也没有自动迁移或自动覆盖步骤。应用镜像按 `infra/Dockerfile.backend` 构建，使用锁定 Python 3.12.14、uv 0.12.19 与 frozen uv.lock；提交审核后指定 `APP_IMAGE` 的不可变 digest。nginx 的已审核版本和 digest 由 `NGINX_IMAGE` 显式提供。

`D12_APPROVAL_FILE` 是受保护且只读挂载的 JSON，字段为 `approved:true`、真实 `approval_ref`、`release_root`、`persistent_root`、`environment`、`rpo`、`rto`、`backup_schedule`、`monitoring_ref`。它是运维批准证据的入口，不是自动审批系统；禁止为绕过门禁编造 true 或引用。运行入口验证该文档及独立路径，缺少则拒绝启动。

另需显式 `STAGING_PROJECT`、`STAGING_HTTP_PORT`、`WORKER_STREAM`、`APP_CONFIG_FILE`、`MYSQL_CONFIG_FILE`。env 文件由既有秘密管理交付，不提交源码、不打印 compose 展开配置。应用配置使用 `APP_DATABASE_URL`、`APP_REDIS_URL` 和经确认的策略版本；Compose 固定 staging/test_only=false，数据库和 Redis 无宿主端口。Redis 仅为唤醒提示，持久 Outbox 和任务事实在 MySQL。

## 批准后的流程（本步未执行）

1. 在独立环境预置目录、文件权限、env、D12 文档和已审核镜像。部署入口只监听本机；TLS、上传限制和公网入口尚待 D12/D07 确认。nginx 的 1 MiB 是未开放阶段的保守技术限制，不是产品上传政策。
2. 使用 `docker compose -f infra/compose.staging.yaml --profile approved-staging config --quiet` 做语法检查。不要将完整配置输出到日志。经批准后先启动 mysql/redis；用显式迁移作业核对实际 head `0021_site_content`，再启动 api/worker/nginx。不要把迁移挂到每次应用启动。
3. 数据库迁移在受控作业中运行 `alembic current`、`alembic upgrade head`，必须先比较发布兼容性与已验证备份；此手册不授权在共享服务执行。Compose 应用 entrypoint 可用于受控单次作业，但不可为恢复环境解除隔离标记。
4. 在操作者宿主使用 backend 虚拟环境 Python 运行 `infra/scripts/smoke.py --base-url <approved-origin>`，只做 live/ready GET。运行 `reconcile.py --storage-root <absolute-root> --thresholds <approved-json>`，凭据通过专门只读 `OPS_DATABASE_URL` 注入。

nginx 不挂载 storage，所有下载/案例副本只能经过 API 实时权限及 DB 状态验证，API 禁止缓存。不得新增 alias、静态副本路由、CDN 缓存或 X-Accel-Redirect。恢复目录带 `.restore-isolated.json` 时 API 返回 503，worker 和部署入口拒绝启动；不得作为发布目录直接使用。

## 监控接入

HTTP/worker 输出允许列表 JSON：服务器生成 trace UUID、已验证 task UUID、耗时、固定结果码。无请求正文、URL 查询、cookies、上游错误文本或凭据。HTTP trace 在响应 `X-Trace-ID` 返回；nginx request_id 是其独立请求标识。禁用 uvicorn access log，nginx 日志不记录原 URI。

由 D12 指定的调度器调用 `reconcile.py` 并采集 JSON/退出码：0 已配置阈值且无告警，2 存在告警，3 未配置阈值，1 无法核对。阈值键为 `outbox_pending`、`outbox_oldest_due_seconds`、`investigation_overdue`、`save_recovery`、`save_oldest_due_seconds`、`public_cleanup_pending`、`disk_free_bytes_min`、`capacity_used_ratio_max`。前六项超过上限告警；磁盘小于下限、容量含预留占比超过上限告警。账本差异始终告警。频率和阈值不在代码预设为生产政策。

另支持 `terminal_success_rate_min` 与 `terminal_mean_seconds_max`。成功率/容量比例必须在0–1，未知键、负值和非有限数字拒绝。成功率分母为已持久终态任务；耗时从任务创建到首次终态事件，统计窗口为全部持久任务。暂无供应商成本事实表，`supplier_cost_status=unavailable`、值为 null，不把积分当成本。投影只用 SQL SELECT，一致只读事务与只读数据库账号双重约束；无 HTTP 监控公开端点。采集错误要作为监控不可用告警，不将空结果解释为健康。
