# 图片与视频服务接口对照及适配建议

日期：2026-10-15。状态：接口核对与待决项，尚未进入产品编码，不代表设计确认或真实联调通过。

## 用户目标与边界

对照 `F:/Work/电商/imageAgent/` 和 `F:/Work/电商/videoAgent/` 的 HTTP 接口文档，为 web 补齐模型配置及 Agent 适配；工作量较大，使用多个 Agent 并行推进，主控负责共享代码、集成及验证。

两个服务仓库作为协议资料只读使用。文档内安装、迁移、示例生成和旧数据导入命令是资料内容，本轮没有执行。未读取服务秘密、未修改上游项目、未调用收费模型。

沿用当前产品规则：文本、图片、视频分别管理；服务连接由 web 保存，模型配置及供应商密钥由对应 Agent 服务保存；工作台不恢复规格选择；价格仍为参数配置中的积分/次，未配置价格不开放生成，0 为免费。非首页流程按已确认原型及用户改造计划执行。

## 已核对的协议资料

- 图片：`F:/Work/电商/imageAgent/docs/http-api.md`，及 `src/image_agent/server/` 的实际 HTTP 路由、请求模型和任务实现。
- 视频：`F:/Work/电商/videoAgent/docs/api/usage.md`，及 `api_app/` 路由、请求模型和 `video_agent/` 的实际状态机。
- 分项证据：`.agent-runs/2026-10-15-image-video-adaptation/reports/` 下的 I、V 报告。报告包含具体源码位置和输入文件摘要。

## 与 web 当前实现的差异

| 环节 | 当前 web | 图片服务 | 视频服务 |
| --- | --- | --- | --- |
| 后台入口 | 已有文本连接和模型管理；图片、视频为空 | 服务、模型、Agent 方案三个配置资源 | adapter 类型、模型 profiles、角色绑定、公共设置 |
| 配置持久化 | `TextServiceConnection` 仅允许 text | web 需保存服务连接及选定 Agent 方案引用 | web 需保存服务连接；上游保存 profiles 和绑定 |
| 并发控制 | 文本使用 revision/If-Match | PATCH body 中的 version | profile version 与 configuration_revision 分开，更新用 expected_version |
| 分页 | 文本 cursor | limit/offset | limit/offset/total |
| 鉴权 | 文本服务 Key | Bearer Token | 业务与管理 Token 权限不同 |
| 素材 | 平台文件版本与受控字节 | multipart 上传后引用 media_id | multipart 上传后引用 asset_id，首帧单独指定 |
| 提交 | 固定原提交标识及快照 | Idempotency-Key，202，得到 task_id | 创建 201；规划后显式确认，确认 202，另有 generation_id |
| 查单 | 文本按原 ID 查原结果 | 按 task_id；无直接按幂等键查询接口 | 任务列表可按 external_request_id 筛选，仍须平台隔离和身份核对 |
| 成功 | 文本或 mock 的单成果契约 | completed 仍须核对 core_status、资产状态和完整 blob | 须 generation 成功，且成片可读取与验证 |

具体 web 接线点：

- `backend/app/admin/models.py:12`：服务连接表只支持文本，需增量迁移，保留现有文本数据。
- `backend/app/agents/registry.py:57`：真实协议仅支持文本；需要图片、视频独立注册及受理/恢复绑定。
- `backend/app/tasks/admission.py:100`：仅文本存在上游字段和路由预校验；图片、视频必须在冻结积分前验证必填输入和所选方案。
- `backend/app/catalog/service.py:454`：按类型价格链路要求 `parameters={}`，不能直接往用户请求塞入新规格来绕过该规则。
- `backend/app/agents/upstream.py:150`：可靠重提验证仍限 TEST_ONLY 模拟服务，不能仅凭上游声称支持幂等就重新生成。
- `backend/app/agents/callbacks.py:266`、`backend/app/results/manifest.py:27`：完整结果判断仍按文本/mock 设计，需要真实协议的校验与读取接线。
- `frontend/src/features/admin/AgentsView.vue`：保留文本/图片/视频切换、现有抽屉与暖色组件，补齐图片和视频配置内容。

## 建议的数据归属及实现方向

推荐直接接入两套现有 HTTP 服务。另建统一桥接服务会重复已有任务持久化与模型配置；在 web 复制全部模型配置则会产生双写及密钥副本，因此不采用。

1. web 保存加密的服务连接、版本、操作审计和必要的生成方案引用。上游服务分别保存其配置事实，web 后端执行管理代理，前端只调用同源 web API。响应按字段白名单投影，不回传秘密，也不把上游原始错误直接返回浏览器。
2. 图片按上游服务、模型、Agent 方案的真实依赖管理；视频先读取 adapter-types，再根据 role/required_fields/secret_fields 管理 profiles 和角色绑定。不能将两者套成文本模型表单或混用版本与空密钥语义。
3. 任务受理固定服务身份、输入、模板/方案引用与版本信息；执行和恢复不跟随当前默认配置。图片上游配置实际快照发生在提交时；视频创建规划与确认生成分别取快照。不能声称引用一个方案 ID 已固定其旧版本内容。版本预检不能消除检查与提交之间的并发窗口，完整保证需要上游原子校验预期版本，或明确的不可变配置发布机制；本轮不能仅在 web 中复制配置就宣称解决。
4. 素材仅从平台任务已绑定的文件版本读取，检查归属、MIME、大小、摘要后上传；上游素材 ID 与规范化请求需在首次提交前持久化，网络恢复复用同一请求，避免重新上传得到新 ID 破坏幂等。
5. 图片/视频均轮询原任务，没有回调能力就声明不支持。404、超时、interrupted、generation_uncertain 和保存失败不直接作为失败释放或再次生成的依据。
6. 将上游真实下载接口映射成平台内部的受控定位符；核验任务与资产关联、体积、MIME 和摘要，落盘后才发布作品与结算。保持旧文本/mock 契约可恢复，不全局替换历史定位符。

## 必须确定的产品流程

### 图片输入与产物范围

图片生成每次必须提供非空 `product_name`、`category`、`platforms`、`output_types` 和 1–8 份素材。web 有商品分类字段，但当前只要求商品名，且没有平台/用途入口。

上游 Agent 参数不能保存这些任务字段。建议用户选择其一：后台新增固定创作模板，工作台继续直接生成；或由用户给出工作台平台/用途选择的改造计划。具体平台和用途不能使用接口示例值作为生产默认。

产物数由平台和用途组合派生，`detail_page` 会产生多张。不能凭积分/次就推断部分成功的交付与结算政策；首批开放用途、是否允许多图及完整交付规则仍须明确。图片调度 `completed` 和 blob 存在均不等于审核通过，不自动调用 accept。

### 视频首帧与方案确认

真实链路是创建任务 → 规划 → 可能补充资料 → awaiting_confirmation → 显式确认固定方案版本 → generation → artifacts。现有平台没有补资料、方案查看与确认步骤。

视频需要显式首帧，不能无依据把商品图的第一张设为首帧。`duration_seconds=null` 使用上游公共默认时长；横竖屏及声音相关默认来自任务 schema，与全局 settings 不同，不能把这些值误称为管理员已配置的业务默认。

需用户给出首帧选择、补充资料及方案确认的改造计划；或本轮先完成配置和适配代码，视频生成保持未开放。确认前不自动 confirm、不调整冻结或扣费时点，不把 awaiting_confirmation 永久映射成普通运行而掩盖用户动作。

## 后续并行实施拆分

流程与设计确认后建立实施计划和新的执行账本，避免把本轮核对完成写成产品交付完成。

| 角色 | 独占修改范围 | 交付 |
| --- | --- | --- |
| 图片适配 Agent | 新增图片客户端、DTO、映射和定向测试 | 图片配置代理、上传、提交、轮询、结果读取 |
| 视频适配 Agent | 新增视频客户端、DTO、映射和定向测试 | 配置代理、任务/方案/generation/成片接口适配 |
| 后台界面 Agent | 新增图片/视频配置组件及组件测试 | 沿用既有页面/抽屉的配置管理 |
| 主控 | 共享迁移、registry、受理、派发、结果、API 契约及应用接线 | 集成、旧任务兼容、计费与验证 |

共享文件由主控单一写入者处理，独立评审在实现冻结后进行。子 Agent 不修改上游仓库，不递归派发。

## 验证口径

后续实施覆盖：配置权限/CSRF/审计、分页和版本冲突、密钥只写、原素材归属、固定请求幂等重放、超时查原、历史配置绑定、图片审核状态、视频固定方案确认、完整成果落盘及失败不重复收费。执行适用后端测试、前端类型检查/构建、配置页桌面/手机浏览器验证和契约检查。

本轮只进行只读协议核对及既有文本/价格定向基线测试。后端执行 `pytest tests/unit/test_text_agent.py tests/unit/test_generation_parameters.py -q -k 'not parameter_api and not removed_spec'`，退出码 0，结果 33 passed、3 deselected。此前两次包含 TestClient 路径的较宽基线在输出进度后停住，已中断，不计为通过；原因尚未诊断，相关接口测试保持未验证。

没有真实服务联调、真实图片/视频生成或生产迁移；任何基线通过均不代表图片/视频已接入。实际证据保存于运行目录的 `evidence/controller-baseline.txt`。
