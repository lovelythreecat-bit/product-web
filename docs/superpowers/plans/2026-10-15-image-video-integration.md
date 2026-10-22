# 图片与视频 HTTP 接入实施计划

> **For agentic workers:** Use superpowers:subagent-driven-development。用户已明确多 Agent 推进与两项工作台改造；沿用当前包含未提交文本配置成果的工作目录，不切换到缺少这些成果的新 checkout，不提交其他既有改动。

**Goal:** 补齐图片/视频后台模型配置、HTTP 适配及用户输入/方案确认链路。
**Architecture:** 上游配置单一归属；web 保存版本化加密连接与不可变任务输入，媒体执行和命令另表持久化；适配器复用现有任务/成果/账本。
**Tech Stack:** Python/FastAPI/Pydantic/SQLAlchemy/Alembic，Vue3/TypeScript，现有 MySQL/Redis 与硬盘。
**Spec:** `docs/superpowers/specs/2026-10-15-image-video-integration-design.md`

## Global Constraints

- 上游仓库只读，不读秘密，不真实生成、不迁移生产、不修改现有生产启用门槛。
- 保留原文本与 mock 任务；原素材、服务连接、请求与结果身份必须固定。
- 维持按类型积分/次、提交冻结、完整成果保存后消费；方案确认不再次收费。
- 不自动确认、重新生成、接受未审核图片或把超时/404判定确定失败。
- 非首页沿用暖色组件；本轮仅实施用户明确选择的字段和流程。

## Review Focus

- 不同资源的版本/空密钥语义不能混用；测试只写 Key 与冲突保护。
- 上传重放不能改变原 body；测试持久映射与未知提交不盲重发。
- 视频旧方案、错任务与重复确认；测试固定版本/原键及多重身份。
- 图片缺张/审核不通过、视频错成片；测试完整成果拒绝与原结果读取。
- 新输入不恢复规格计价，历史请求及原价不变；执行报价/受理回归。

## C：配置与传输（并行）

Files: 新增 `agents/media_http.py`、`media_connection.py`、`media_runtime.py`，`admin/media_agents.py`、`media_schemas.py`，迁移0027，相关新单测。

Interfaces: `MediaClient(base_url,service_key,timeout=30,max_response_bytes=...).json(method,path,body=None,idempotency_key=None)->(status,payload)`；`upload(path,data,mime,fields=None)->dict`；`download(path)->(bytes,mime)`；`MediaServiceError(status_code=503,public_message=None)`。连接 `read_media_connection(session,settings,kind,connection_id=None)` 返回含 id/base_url/service_key/management_key/default_config_id/image_model 的模型。`managed_media_agent_id(mode,kind)`、`managed_media_input_support(kind)`、`sync_media_agent(session,settings,kind)` 发布代码维护身份。

- [x] 先写配置权限、版本、加密/只写、分页/响应白名单及 HTTP 拒重定向测试并确认失败。
- [x] 实现实际三组图片配置和视频资源管理代理，连接留历史版本，新增管理 API。
- [x] 单测与 Ruff 验证；报告实际命令/退出码。

## I：图片协议（并行）

Files: 新增 `agents/image.py` 与图片单测，仅此范围。
Interfaces: `ImageAgentProfile` 包含 base_url/service_key/agent_config_id/image_model/max_result_bytes；`build_image_request(snapshot,profile,uploads=None,validate_only=False)`；`ImageAgentAdapter(profile=...,external_submission_id=...,material_loader=...,load_state=...,save_state=...)` 实现实际 worker adapter 方法。素材 loader 返回按原 material_versions 排序的 `{file_id,version,content,media_type,sha256}` 数组；load/save_state 为持久 JSON 读取/patch。

- [x] 先测平台/用途组合、分类/素材必填、审核/缺张、不确定不重提。
- [x] 实现 multipart media、精确 body 持久化、提交/轮询/成果受控读取；无外部查询声明 unsupported。
- [x] 定向测试与 Ruff，交主控接线。

## V：视频协议（并行）

Files: 新增 `agents/video.py` 与视频单测，仅此范围。
Interfaces: `VideoAgentProfile` 包含 base_url/service_key/max_result_bytes；`build_video_request(snapshot,uploads=None,validate_only=False)`；`VideoAgentAdapter` 同图片构造参数，实现 submit/query/retrieve 与 `confirm(plan_version,idempotency_key)`、`update_inputs(body,idempotency_key)`。视频 metadata 保存 status/questions/head_plan_version/plan/generation_id，query 绝不确认方案。task 和 generation/plan/artifact 全部核对。

- [x] 先测首帧归属、补资料/等待确认不触发 confirm、旧方案与错成片拒绝。
- [x] 实现上传、规划、原 ID 查单、显式命令及完整成片受控读取。
- [x] 定向测试与 Ruff，交主控接线。

## M：主控集成与界面

Files: 新增媒体执行/命令 models/store/routes（迁移0028），修改 registry/admission/catalog/result/callback/task-detail；新增后台媒体配置组件、工作台字段和视频任务面板/API/类型。

- [x] 新增受理/输入/命令持久化定向测试并执行旧协议回归；主控初始 RED 原始输出未单独留档，不以本勾选补造证据。
- [x] 接线版本化连接、持久上传映射和原任务交互命令；网络 I/O 不放在受理事务或查询 GET 中。
- [x] 工作台图片单平台/用途、视频显式首帧；视频方案抽屉及资料补充和费用说明；后台按资源真实结构管理。
- [x] 更新 OpenAPI/TS，执行后端定向回归、前端测试/类型/构建、桌面与手机浏览器检查。

## R：独立评审与交付

- [x] 冻结相关源码快照，独立检查接口/权限/资金/恢复与界面实现，修复实际问题并重跑受影响验证。
- [x] 更新产品设计与验证记录，账本记录证据和未验限制；不将离线替身通过称为真实模型联调通过。

## 最终验证范围（2026-10-16）

上述勾选表示本轮代码与离线验证交付，不代表生产或真实 Agent 生成验收。后端390通过/471跳过；前端130通过；类型、构建、契约检查通过；Edge媒体旅程与分类回归共4项通过。独立R/G评审发现的问题已修复并定向复核。本机mock仅新增迁移至0028；临时API/Vite已停止，原有用户进程保留。详见 `docs/verification/image-video-integration-2026-10-16.md`。
