# 视频 Agent 配置重做

用户要求按 `F:/Work/电商/videoAgent/` 实际参数完全重做，并确认三类模型直接配置、运行设置、声音设置，以及既有服务连接和编辑抽屉。

## 实际参数依据

- `video_agent/factory.py`：真实模型仅 `openai_chat`（分镜）、`seedance` / `wan`（视频）、`openai_vision`（视觉）；均需 API 根地址、模型名、API Key，万相额外必填单段最长秒数。
- `video_agent/config.py`：万相单段 1–15 秒；成片时长档 1–30 秒且不重复，默认时长属于可选档；最多 12 图、单文件最多 20 MiB；码率为正整数，租约至少 15 秒；八种输出比例固定，尺寸为正偶数且符合比例。
- `api_app/routes/settings.py`、`api_app/schemas.py`、`video_agent/settings_service.py`：HTTP 公共设置不接受桌面适配器字段，模型 profile 与角色绑定独立版本化；页面不能直接照搬桌面设置请求。
- `desktop_app/settings_dialog.py`、`video_agent/pipeline.py`：有声请求视频供应商音轨，缺少供应商音轨时本地占位回退；当前没有独立真实配音、音乐接口。

## 实现

视频页面直接展示分镜文本、视频生成、视觉检查三种用途，按用途分别打开编辑抽屉。视频供应商切换明确区分 Seedance / 万相；视觉检查可关闭。没有 profile 列表、手工角色绑定和 JSON 编辑框。运行设置提供出片方式、成片时长、文件/编码限制及八比例宽高字段；声音单独保存。继续复用 V2 暖色和 Element Plus 公共控件。

新增 GET `/api/v1/admin/media-agents/video/models`、PATCH `/video/models/{planner|video|visual}`：读取上游绑定及已绑定模型，保存前检查 web 连接 revision、上游 configuration_revision 和模型身份/version；同地址同供应商无新 Key 时原子更新原模型并保留其他参数；新 Key 创建新模型，再以精确配置修订绑定。绑定失败保留旧绑定，可能留下未引用的新 profile，不自动删除或重复提交。视觉关闭解除绑定而不删除旧 profile。所有模型凭据仍只存上游；响应只返回 Key 存在状态，审计只记录角色和版本。

新增 GET/PATCH `/api/v1/admin/media-agents/video/audio`：声音偏好写入现有不可变连接的加密载荷，无新增数据库列或迁移。受理时将选择固定到任务路由，Worker 使用原路由；历史连接及未携带该字段的旧任务按无声处理。有声/无声都保留上游 fake 本地回退，是否请求/导出音轨由任务固定标志控制，避免关闭声音破坏尚未确认的旧有声任务。密钥轮换保留可读取的偏好；旧加密主密钥不可用且完整替换服务凭据时，未知偏好安全恢复为无声。

模型、运行设置和声音分别保存；不承诺跨服务数据库原子性。上游返回超时或部分保存失败时必须重新打开读取真实状态，不自动重放写操作。视频规划/确认使用上游各自时刻的配置快照，既有接口没有提交时 expected_config_version；不把本地预读描述成消除了该窗口。没有执行真实模型生成、修改 videoAgent 源码、写入生产配置或改变计价与启用门槛。

同 Key 的现有 profile PATCH 仅接受模型 version，不接受全局配置修订；因此写后核对精确修订增量和当前绑定身份/version，检测到外部改绑或设置变化返回 409。这个窗口中旧的、已解除绑定的 profile 可能已经更新，但不会改写新绑定或虚报成功。运行设置读取前后核对服务连接修订，保存携带 `expected_connection_revision`，服务端在调用上游前锁定并比较，避免陈旧草稿写入替换后的服务。

独立代码复核指出的旧有声任务回退、模型重绑假成功及运行设置连接替换三个问题均已修复并复核，无剩余相关发现。

共享抽屉做局部焦点修复：Element Plus 选择器先聚焦真实输入而非 tabindex=-1 包装层；配置读取期间保留触发按钮焦点，关闭后恢复。

## 验证

- 后端视频配置、视频协议和媒体代理相关回归：82 项通过，包含模型重绑竞态、替换服务连接时拒绝陈旧运行设置，以及关闭声音保留旧任务回退。
- 使用 videoAgent 实际 `SettingsService` 和临时隔离 SQLite 数据库完成三类模型配置、万相切换 Seedance、切换真实模式及脱敏检查；无生成调用。
- 前端完整单测：191 项通过。并发和抽屉修复后相关 17 项再次通过。类型检查和生产构建通过。
- 后端全量单测：466 项通过、3 项失败。失败均涉及测试夹具没有提供任务时间字段：`test_display_numbers.py::test_task_projection_preserves_number_across_state_changes_and_replay`、`test_display_numbers.py::test_task_detail_contains_persisted_owned_conversation_number`、`test_generation_parameters.py::test_original_admitted_intent_replays_without_using_new_prices`。这些任务时间字段行为没有在本次修改；不把全量后端报告为通过。
- 桌面 1440×1000、手机 390×844 使用 TEST_ONLY 接口数据验证实际 Element Plus 操作：10 项通过，覆盖模型编辑、供应商切换、万相秒数、密钥保留/取消清空、初始焦点和关闭恢复、运行/声音保存、原文本/图片入口及公共控件。截图见同目录 `screenshots/video-agent-configs-2026-10-17-{desktop,mobile}.png` 及 `video-agent-drawer-2026-10-17-{desktop,mobile}.png`；截图不代表真实供应商生成验收。
- 新界面机械设计检测：无发现。OpenAPI 及前端契约同步。
