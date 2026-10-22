# 图片生成队列专项验证（2026-10-20）

## 上游事实

只读检查 `F:/Work/电商/imageAgent/src/image_agent/server` 与配置中的非敏感字段，未读取输出密钥。

- 检查时 `server.config.json` 的 `worker_concurrency=1`、`queue_capacity=100`。
- `worker.py` 按配置创建 N 个异步 worker；任务接受后由 worker 执行，HTTP 返回不代表任务结束。支持配置 6 个 worker；实际供应商吞吐、费用及负载能力未通过真实生成验证。
- `task_service.py::_submit_task` 先检查已有幂等键，再统计 `queued + running`。达到 100 时，在创建 `HttpTask` 之前抛出 `ServerError(429, "queue_full", ...)`。因此容量是排队和运行任务合计；6 个运行任务时最多还可保留 94 个排队任务。
- 错误响应为平铺 JSON：`{"code":"queue_full","message":"Task queue is full","request_id":"…"}`；没有 `Retry-After`。202 正常响应含 `task_id/status/core_status/config_versions/progress/error`。

## 本次图片适配器修复

`image.py` 只在提交 `/api/v1/tasks` 时识别共享传输层确认的 HTTP 429、`queue_full`、未携带任务资源的入队前拒绝，返回 `RATE_LIMITED`。默认等待 5 秒，保留有效的 1–3600 秒上游建议。

每次 POST 之前持久化新的 `submission_attempt_id` 并清空旧拒绝标记。明确拒绝后保存当前 attempt、外部提交 ID、服务 scope、不可变请求摘要和等待时间。`submission_started` 保持单向，不重置素材上传状态。下一次提交必须通过可信组合层的 `authorize_submission_retry()`；缺少授权、未知响应、断开连接、超时、错误格式的 429 或上传拒绝都不允许重放。重试复用已保存的素材 ID、完整请求体和原幂等键。

共享数据库授权、每次上游尝试的拒绝证据、任务状态回到 QUEUED、长期异步容量槽与积分由主任务集成及验证；本专项未修改这些文件。

## 已执行验证

| 命令（在 backend 目录执行） | 结果 |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/unit/test_image_agent.py -k 'queue_rejection or ambiguous_rejections' -q`（实现前） | exit 1，1 failed / 6 passed；复现明确入队拒绝错误地变成 UNKNOWN |
| `.venv/Scripts/python.exe -m pytest tests/unit/test_image_agent.py -q`（最终） | exit 0，81 passed |
| `.venv/Scripts/python.exe -m pytest tests/integration/test_image_agent_pipeline.py -q` | exit 0，8 passed；真实本机 HTTP、真实 MediaClient 与状态合并器，无付费生成 |
| `.venv/Scripts/python.exe -m ruff check app/agents/image.py tests/unit/test_image_agent.py tests/integration/test_image_agent_pipeline.py` | exit 0，All checks passed |

HTTP 回归覆盖：真实平铺 queue_full 响应；相同字节请求、素材和幂等键重试；首次拒绝后的第二次 POST 超时或断连不能触发第三次 POST；无效 JSON、不同错误码、缺失错误码、携带 task_id 的 429 和素材上传 429 均保持 UNKNOWN。

另一次未指定数据库目标的裸 `pytest -q` 启动后，按主任务协调要求中止以避免重复全量运行。进程 exit 1，只有未完成的点号/错误进度输出，无测试名称和诊断摘要；不能视作全量通过。最终共享全量和 SQL 验证以主任务报告为准。

## 范围限制

本专项未修改或重启上游服务，未修改上游配置，未执行真实付费图片生成。上游 worker 调整、生产启动参数确认、异步容量槽和 MySQL/Redis 状态机验收由主任务负责。此报告中的 1/100 是检查时观测值，不能代替部署后的运行态证明。
# 主任务集成补充

主任务已接入数据库异步额度、每次提交的拒绝证据授权、崩溃恢复和运行配置；统一验收与本机生效情况以 [媒体队列统一验证](media-generation-queue-2026-10-20.md) 为准。下方保留图片专项实施时的检查记录。
