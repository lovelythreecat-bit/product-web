---
status: draft
implementation_status: planned
review_required: true
---

# 快速生成页面上下文契约（建议稿）

本稿供后续前端与客服集成使用，不改变现有流程。“可直接获取”指已有前端内存或业务响应字段可供未来适配器读取，不代表已经发送给客服，或已实现定位、高亮、自动操作。本轮未调用业务接口。

## 页面与最小结构

路由 `/workspace/quick/:runId?`，`/workspace` 重定向到快速生成。四阶段是商品确认、营销文案、图片生成、视频生成；`step=5` 是成果汇总完成态，不是第五个收费阶段。

依据：`frontend/src/router.ts:22-29`；`frontend/src/features/quick-generation/useQuickGeneration.ts:51-119,234-250,284-344,412-438`；同目录 `QuickGenerationView.vue:19-23,47-55,135-219`；`backend/app/quick_generation/service.py:477-515`。完整来源见 [source-index.json](source-index.json)。下文省略目录的快速生成组件均位于 `frontend/src/features/quick-generation/`。

| 建议字段 | 含义与最小值 | 当前来源 | 后续开发 |
| --- | --- | --- | --- |
| schema_version / context_revision | 契约版本、页面状态版本 | 暂无客服契约 | 建议新增；切页、编辑、任务更新时递增 |
| page_id / route_template | quick_generation / 路由模板 | router | 白名单映射；不发送路由中的真实业务编号 |
| current_step / progress_step | 正在查看步骤、持久化到达步骤，1–5 | step / progressStep | 必须分开输出 |
| active_panel | main/copy_requirements/image_requirements/charge/video_plan/video_edit/video_confirm/video_inputs/history | open 状态散落各组件 | 建议新增统一映射 |
| read_only / dirty / product_dirty | 完成态、草稿和商品未保存修改 | readOnly / dirty；商品编辑器暴露 dirty | 聚合布尔值，不传正文 |
| request_state | idle/loading/saving/submitting/unknown | loading/busy/uncertain | busy 未完全细分，不猜操作类别 |
| fields[] | 标识、显示名、必填、已填、校验 | 表单与 requiredFields | 统一字段状态和错误白名单 |
| uploads | uploading、saved_count、limit、save_state | uploading、material_versions.length、常量 | 没有统一百分比/逐文件队列；不编造 |
| tasks[] | 本地别名、类型、是否当前批次/阶段、任务和结算状态、必要媒体阶段 | run.tasks/currentItems/TaskDetail/media | 严格筛选，禁止发送完整 TaskDetail |
| actions[] | 标识、按钮名、可见、可用、不可用原因、校验就绪、定位键 | v-if/disabled/校验函数 | 没有统一动作或原因列表，需开发 |
| quote | known/unknown、credits（可选）、freshness、confirmed、read_error | estimated/pendingBatch/业务报价 | 区分估算和受理报价；不能从文章填价格 |
| evidence_freshness | 页面采集时间、最近业务读取时间、过期/失败 | 无统一时间元数据 | 建议新增；旧值保留但标 stale |

`fields[]`：`field_id, label, required: true|false|unknown, filled: true|false|unknown, validation: not_checked|valid|invalid|unknown, error_code?, safe_error?, locator_key?, locator_status`。未知不等于 false。必填项须说明作用阶段：商品表单 requiredFields 来自文案能力，图片/视频还会按自身能力校验。未读取能力时不能猜必填项。

`actions[]`：`action_id, label, visible, enabled, disabled_reasons[], validation_ready, locator_key?, locator_status`。enabled 与 validation_ready 分开：按钮可点击仍可能在提交时校验失败。当前多处只生成整段错误，逐字段 validation、结构化不可用原因都需要后续开发。

## 商品确认（步骤 1）

依据：`QuickProductEditor.vue:20-67`；`useQuickGeneration.ts:91,234-250,351-365`；`QuickGenerationView.vue:24-30,111-121,143-145,197`；`frontend/src/features/workspace/productTypes.ts:1-34`、`display.ts:2-13`。

| field_id | 显示名称 | 必填与校验 | 已声明定位 |
| --- | --- | --- | --- |
| product.name | 商品名称 | 必填、非空 | #quick-product-name |
| product.product_type | 商品类型 | 必填、实际类型枚举 | #quick-product-product_type |
| product.category | 商品品类 | 动态必填标记可能存在；保存时为空按所选类型名称补入，不代编具体品类 | #quick-product-category |
| product.brand / origin | 品牌 / 产地 | requiredFields 决定 | #quick-product-brand / #quick-product-origin |
| product.{key} | 当前规格字段 | requiredFields 决定；其他为选填 | #quick-product-{key} |
| product.description / sellingPoints | 商品卖点与说明 / 历史核心卖点 | 根据字段替换与 requiredFields | #quick-product-description / #quick-product-sellingPoints，只有渲染者可定位 |
| product.audience / scene / price / promotion / warranty / notes | 适用人群 / 使用场景 / 实际售价 / 优惠信息 / 售后保障 / 补充说明 | requiredFields 决定 | #quick-product-{key} |
| product.extra.{key} | 已有补充资料的实际显示名 | requiredFields 决定 | 已有动态 ID；自定义 key 和标签须过滤 |
| materials | 商品参考图 | 是否必填及最少数量取决于阶段能力 | input 的 aria-label=上传商品图片；上传按钮稳定标识建议新增 |

规格字段按类型显示，显示名复用 `display.ts` 字典，不能让模型临时翻译：

| 商品类型 | 实际字段键 |
| --- | --- |
| 服饰内衣 | fabric,size,color,fit,season,care,package |
| 鞋靴箱包 | material,size,color,lining,sole_material,weight,package |
| 美妆个护 | skin_type,ingredients,net_content,shelf_life,usage,package |
| 食品饮料 | flavor,net_content,ingredients,allergens,shelf_life,storage_conditions,package |
| 数码电子 | processor,memory,storage,screen,battery,connectivity,compatibility,package |
| 家居日用 | material,color,size,weight,capacity,package |
| 家用电器 | power,voltage,energy_rating,size,weight,functions,package |
| 运动户外 | sport,material,size,weight,waterproof,package |
| 母婴玩具 | age_range,material,safety_standard,size,weight,package |
| 其他商品 | material,color,size,weight,technical_specs,package |

这些字段只提供已填与校验状态，不提供商品原值。长字段最多600字符，其余文本最多120字符，为当前前端输入限制，不代替业务能力校验。

“保存商品资料”在 busy/disabled 或已保存且无修改时禁用；“确认商品，生成文案”在 blocked 或商品保存中禁用，点击仍须保存、校验。按钮没有稳定业务 ID，建议新增 `quick.product.save`、`quick.product.open_copy` 定位键；已有 `#quick-product-form` 是表单。

当前新上传/新生成参考图上限4；旧文档20张与草稿容纳20条的差异见审核清单。上传时传 uploading，不虚构百分比；文件内容、名称、地址、真实编号默认不传。

### 文案创作要求弹窗（可从步骤 1 或 2 打开）

依据：`QuickCopyRequirements.vue:15-45`；`frontend/src/features/workspace/TextChoices.vue:24-51`；`QuickGenerationView.vue:73-81,210`。

| field_id | 显示名/必填 | 校验与状态 | 定位 |
| --- | --- | --- | --- |
| copy.types | 文案类型，必填 | 至少1种、最多7种，每种1–100字符；传数量/合法性，不传自定义名称全文 | aria-label=文案类型、动态useId；稳定键建议新增 |
| copy.platform | 目标平台，非必填 | 默认淘宝，选填文本 | TextChoices动态ID及aria-label；按弹窗作用域定位 |
| copy.tone | 语气，非必填 | 默认自然，选填文本 | 同上，aria-label=语气 |

“确认生成文案”仅 busy 时禁用；prepared 时字段锁定；校验失败在点击后提示。费用“—”不是免费。报价相同可直接提交，变化时须核对新费用，不能保证一定另弹收费框。提交不明时按钮可能为“核对原批次”。建议新增 `quick.copy.submit`。

## 营销文案（步骤 2）

依据：`useQuickGeneration.ts:61-85`；`QuickGenerationView.vue:147-158,198`；`backend/app/quick_generation/service.py:483-504`。

| field_id | 显示名/必填 | 校验来源 | 定位 |
| --- | --- | --- | --- |
| copy.result | 单一营销文案，确认时非空 | copy_text.trim，长度最多100000 | #quick-copy-text |
| copy.results.{local_key} | 各类文案，确认时每项非空 | copyEntries对应copy_texts，组合总长也不得超过100000 | #quick-copy-{index}；索引会变，建议稳定项键 |

实际单/多文案二选一。只传非空、是否超限，不传正文。可编辑要求 complete 且无 blocked；完成流程只读。主要动作有复制/复制文案、重新生成、历史版本、查看原始任务、重新选择文案类型、调整创作要求、确认文案，生成图片。

“确认文案，生成图片”要求 `!blocked && complete && copyReady`。complete 是当前项全部 SUCCEEDED 且 CONSUMED。主要按钮稳定标识建议新增 `quick.copy.confirm`、`quick.copy.regenerate.{local_key}`；`#quick-original-tasks` 是已有原任务区域。免费次数以业务结果核对。

确认文案成功后 progress_step 可为3，current_step仍为2，并打开图片选择弹窗。这不是需要再次确认文案的错误状态。

## 图片生成（步骤 3）

依据：`QuickGenerationView.vue:160-165,199-200,211-217`；`useQuickGeneration.ts:14-19,239-250`；`backend/app/quick_generation/service.py:505-510`。

| field_id | 显示名/必填 | 校验 | 定位 |
| --- | --- | --- | --- |
| image.platform | 目标平台，必选 | 当前实际枚举，无默认代选 | #quick-image-platform |
| image.outputs | 图片内容，至少一种 | main_image/detail_page/long_image，最多3类 | 复选框无业务ID；建议新增 quick.image.output.{type} |

只传选择数量、成果完成数量、任务与结算。详情图3张一组，主图、长图各1张；全选为5张成果，不是5张输入参考图。

“确认费用并生成图片”打开选择框，“确认生成图片”点击后仍校验平台、类型与能力。存在当前图片任务时，“确认图片，继续视频”要求 `!blocked && complete`。失败已释放可有“重新生成此项”，须重新确认费用；失败仍冻结走任务卡重试/释放。建议新增 `quick.image.open_options/submit/confirm/regenerate_item` 定位键。

## 视频生成（步骤 4）

依据：`useQuickGeneration.ts:94-119,243-249`；`QuickGenerationView.vue:169-171,201-202`；`frontend/src/features/workspace/VideoTaskPanel.vue:52-177`；`backend/app/quick_generation/service.py:215-255`。

| field_id | 显示名/必填 | 校验与必要状态 | 定位 |
| --- | --- | --- | --- |
| video.first_frame | 视频首帧，必选 | 是否已选且属于有效候选；候选类型uploaded/current_confirmed_output，不传真实file_id | name=quick-first-frame；稳定选项键建议新增 |
| video.supplement | 补充资料，等待补充时必填 | 非空且最多10000字；不传问题/答案全文 | #video-text-{taskId}，真实编号仅本地映射 |
| video.shots.{local_key}.{field} | 画面、动作、景别、运镜、字幕、旁白 | 非统一必填；景别/运镜最多1000，其余10000字符；是否可编辑由方案决定 | {taskId}-shot-{index}-{key}；data-shot-content仅对应画面 |
| video.music_direction | 音乐方向，选填 | 最多10000字符、是否修改 | {taskId}-edit-music |
| video.replan_instruction | 调整要求，选填 | 最多9800字 | {taskId}-replan-text |

视频子状态提供 pending/planning/queued/awaiting_input/awaiting_confirmation 或业务实际状态，并聚合 plan_loaded、plan_is_current、revision_pending、waiting_new_plan、command_pending、storage_blocked。来源已在 VideoTaskPanel 中存在，客服聚合接口需开发；子状态不代替 task.state 与 settlement_state。

| 按钮 | 实际主要条件 | 已声明定位 |
| --- | --- | --- |
| 确认费用，生成视频方案 | 无当前视频项且!blocked；点击仍校验首帧、费用 | 建议新增 quick.video.prepare |
| 重新读取图片 | 候选读取报错 | 建议新增 quick.video.reload_frames |
| 查看并确认方案 | awaiting_confirmation，无busy/pending；函数拒绝未完整读取或等待新版 | [data-view-plan] |
| 编辑方案 / 重新生成方案 | 允许修订且待确认，无待核对操作，函数检查版本 | [data-edit-plan] / [data-replan] |
| 保存方案 / 确认方案（编辑抽屉） | 无busy/pending/waitingVersion/readingPlan，修改后先保存 | [data-save-plan] / [data-edit-confirm-plan] |
| 确认此方案 | 仍待确认，无busy/pending；后续函数拒绝未读完新版 | [data-confirm-plan] |
| 确认并继续生成 | 无busy/pending；函数核对当前版本 | [data-send-confirmation] |
| 补充资料 / 提交补充资料 | awaiting_input，无busy/pending，非空且不超限 | [data-open-inputs] / [data-send-inputs] |
| 核对并重试原操作 | pending且非busy | [data-retry-command] |
| 完成并汇总成果 | !blocked且complete；后端检查文案、图片确认仍有效 | 建议新增 quick.video.finish |

已有选择器仅为源码声明，未做浏览器可定位性验收。重复任务卡/弹层须用本地作用域定位，不能将 data 属性当作已有客服控制接口。

## 汇总与全局动作

依据：`QuickGenerationView.vue:135-140,173-219`；`useQuickGeneration.ts:318-344`；`frontend/src/components/TaskCard.vue:36-66,90-120`。

progress_step=5 时所有阶段只读，无编辑必填项。提供各类成果是否可读、复制/预览/下载状态即可，不传内容。汇总“完成并查看作品”到 /works，头部为“返回作品”。“下一步”“查看汇总”只是只读导航，不收费。

| 动作 | 主要条件/后果 | 定位 |
| --- | --- | --- |
| 保存并退出 | 非只读；检查busy/productEditor.busy/uploading/conflict，保存仍可能失败 | 建议新增 quick.save_exit |
| 上一步/步骤导航/下一步/查看汇总 | navigationBlocked为false，目标<=progress_step；导航与生成须分开ID | 步骤区域aria-label=快速生成步骤；稳定按钮键建议新增 |
| 核对原批次费用 | uncertain且pendingBatch；busy禁用 | 建议新增 quick.check_batch |
| 刷新进度 | error且非conflict | 建议新增 quick.refresh |
| 重新读取进度（放弃本页未保存修改） | conflict；会丢弃未保存内容 | 建议新增 quick.reload_progress |
| 重试/释放积分 | FAILED+FROZEN；停止图片可重试是独立特例，仍需服务端核验 | [data-failed-retry] / [data-failed-release] |
| 确认重试/确认释放积分 | 无actionBusy/pendingAction，用户确认 | [data-confirm-failed-action] |
| 重试原操作（失败任务操作） | pendingAction且非只读 | [data-repeat-failed-action] |
| 重新读取作品 | 作品读取失败 | [data-work-retry] |

任务卡已有 [data-task-id]，真实编号仅用于前端本地映射，不进入通用知识图谱。统一定位服务、滚动、高亮、目标存在/可见检查均建议新增，不授权客服代替用户提交、确认费用、删除或释放积分。

## 下一步判定

blocked = readOnly || busy || uploading || locked || uncertain || conflict。locked 检查整个流程任务：任何非成功/失败/人工关闭状态，或 FAILED且FROZEN，均阻止普通修改。当前阶段完成不代表全流程无阻塞。

navigationBlocked = busy || productEditor.busy || uploading || uncertain || conflict || chargeOpen。它与 blocked 不同，运行中某些已到达阶段仍可查看。

建议原因码：READ_ONLY、OPERATION_PENDING、UPLOAD_PENDING、TASK_ACTIVE、FAILURE_HOLD、SETTLEMENT_PENDING、SUBMISSION_UNKNOWN、VERSION_CONFLICT、REQUIRED_MISSING、INVALID_INPUT、QUOTE_UNKNOWN、READ_FAILED、STATE_UNKNOWN。当前没有统一原因枚举，需后续适配，尤其要区分按钮禁用与点击后校验失败。

指导顺序：核对上下文版本与路由 → current_step和active_panel → 状态是否新鲜 → 处理原操作不明/冲突 → 按真实校验补缺或等待 → 只推荐可见、可用且校验就绪的动作。未知时追问或刷新，不能从图谱路径补造状态。收费或破坏性操作仍由用户在原界面确认。

## 隐私与实时性

不传密码、密钥、Cookie、令牌、联系方式、商品/文案正文、图片、下载地址、历史聊天、完整任务快照。错误映射为白名单代码和必要短文案，不直接转发异常堆栈。自定义标签也须过滤，必要时用“文案1”“扩展资料1”。

页面状态只用于当前轮指导，不写入 Chroma 通用文章或 Neo4j 通用图谱。费用、免费次数、任务和结算以业务接口实时响应为准；前端按钮不替代后端授权。读取失败标未知/过期，不从静态文章补全。

## 虚构测试示例

以下是合成契约样例，不是线上请求或真实用户数据。缺失字段不可推断为false。

```json
{
  "synthetic": true,
  "data_origin": "fictional_test_fixture",
  "schema_version": "draft-1",
  "page_id": "quick_generation",
  "route_template": "/workspace/quick/:runId?",
  "current_step": 2,
  "progress_step": 2,
  "active_panel": "main",
  "read_only": false,
  "fields": [{"field_id":"copy.results.item_2","label":"文案2","required":true,"filled":false,"validation":"invalid","error_code":"REQUIRED_MISSING","locator_status":"suggested"}],
  "tasks": [{"local_key":"fictional_task_1","kind":"copy","state":"SUCCEEDED","settlement_state":"CONSUMED"}],
  "actions": [{"action_id":"quick.copy.confirm","label":"确认文案，生成图片","visible":true,"enabled":false,"disabled_reasons":["REQUIRED_MISSING"],"validation_ready":false}],
  "quote": {"freshness":"unknown"}
}
```

正确指引：先补齐“文案2”，再由前端重新检查本阶段全部任务、结算与按钮状态。不能根据一个任务样例认定全部完成，不能声称已替用户填写。
