---
status: draft
review_required: true
---

# 人工审核清单

本轮只核对本地文件。全部文章、图谱和契约均未正式准入；评测题未运行模型。请审核人逐项记录结论、适用版本与日期，未解决的冲突不要由客服自行选规则。

## 待确认业务规则

- [ ] 当前生产使用的代码/配置版本、快速生成各阶段开放情况、实际可用能力和动态必填字段。依据：`backend/app/catalog/service.py:450-485`，本轮没有查询真实配置。
- [ ] 参考图数量最终按4张还是20张；历史超限草稿如何向用户说明。现有执行为4张，详见C01。
- [ ] 文案/图片单项前三次免费重新生成的正式政策、计次范围、是否已对生产开放；不得扩展到视频、失败重试或重新选择整批内容。依据：`backend/app/quick_generation/service.py:299-325,425-432`。
- [ ] 详情图完整3张的交付与计费政策、部分缺失的处置是否完成生产确认。代码按图片价格×3报价，不代表允许按实际交付张数扣费。依据：`backend/app/catalog/service.py:499-502`；需求终稿`:188-190,379`（D-04）。
- [ ] 当前各创作类型价格、注册赠送额度、服务启用条件。资料不写固定金额，不读取配置。依据：`backend/app/catalog/service.py:464-474`、`backend/app/auth/service.py:73-123`。
- [ ] 待核查/保存失败的负责人、证据要求、核查期限和迟到成果政策；不编造释放、退款、补偿时限。依据：需求终稿`:201,383`（D-08）。
- [ ] 人工帮助的真实入口、在线时段、可收集的最少信息；当前资料不声称已转接或已创建工单。用户自助找回与管理员身份核验的对外流程待确认。依据：需求终稿`:382`（D-07），`backend/app/admin/user_management.py:237-250`。
- [ ] 单文件上传的当前政策、删除恢复与存储清理政策；不要把首帧20 MiB上限泛化为所有上传。依据：`backend/app/storage/service.py:28-57`、`backend/app/works/lifecycle.py:28-34`、需求终稿`:384-385`（D-09/D-10）。
- [ ] 页面上下文传输、脱敏、保留期限、定位范围与状态时效阈值；本轮只交建议契约，没有实现客服接入。

## 文档与代码冲突及实现风险

| 编号 | 证据与差异 | 对资料的处理 / 待确认 |
| --- | --- | --- |
| C01 | `docs/product-design.md:51`写20张；`frontend/src/features/workspace/materialLimits.ts:2`与`backend/app/common/types.py:12`均为4。`backend/app/quick_generation/schemas.py:17`仍容纳20条；`service.py:264-268,287,414`限制新增/新生成 | 说明当前执行4，不声称错误提示只是笔误。quick-upload暂缓导入；确认最终规则和文档维护方案 |
| C02 | `docs/product-design.md:63`早期写视频首帧仅上传素材；`docs/design/quick-generation-ui-2026-10-21/README.md:53`已记录支持本次确认生成图；前后端 `useQuickGeneration.ts:94-119` / `service.py:215-255`一致支持 | 历史记录有先后差异，当前资料采用代码与较新说明；人工确认生产版本，不引导选择任意旧任务图 |
| C03 | 同早期条目称视频方案只读；较新`product-design.md:51`和`VideoTaskPanel.vue:95-116,169-177`已有编辑/重新规划 | 采用较新已实现交互，仍要求保存并完整读取新版本再确认 |
| C04 | 需求终稿`:197`写失败自动释放；`product-design.md:63`及`tasks/state_machine.py:166-168`、`tasks/failed_actions.py:97-130`支持失败仍冻结、用户重试或释放 | 采用当前双状态说明，不承诺所有失败都已返还；人工确认适用版本与用户可见政策 |
| C05 | 需求终稿`:174-190`使用规格计价；`product-design.md:93`改按创作类型，`catalog/service.py:464-542`实际读类型价格且详情图乘3 | 不让用户寻找已移除规格选择；金额由实时接口，详情图计费需政策审核 |
| C06 | `QuickCopyHistory.vue:14-29`需要旧批次任务在run.tasks中；`backend/app/quick_generation/service.py:191-205`跳过非当前文案批次，仅对旧图片保留特例 | 代码级风险，未做运行时复现。quick-history暂缓导入；验证旧文案返回与原成果查看，不承诺历史恢复完整 |
| C07 | `QuickProductEditor.vue:34-43,64-66`商品品类可显示动态必填，同时保存逻辑可补默认品类；原生required与自定义校验可能表现不同 | 不声称品类一律选填或一律要手填。需审核实际动态字段与运行时校验；上下文标明阶段与来源 |
| C08 | `QuickGenerationView.vue:201`视频方案按钮仅按blocked禁用；`useQuickGeneration.ts:243`在点击时校验首帧。图片选择也存在可点击但输入尚未完整情况 | 契约区分enabled与validation_ready，客服不可把可点当作可提交；无需擅改代码 |
| C09 | `CustomerServiceView.vue:80-96`有演示和专属记忆宣传；`:15-31`仅本地规则回复；`product-design.md:13`明确未接实时客服 | 仅把演示边界写入文章。实时检索、页面感知、记忆放planned，不承诺已接入 |
| C10 | 单项免费重新生成已有`service.py:317,432`与前端提示，但早期需求`:205`只描述新请求按新价；本轮未取得完整生产促销政策证据 | 不把局部代码扩展成平台永久免费政策，quick-regeneration暂缓导入 |

表中 `service.py` 未另注时指 `backend/app/quick_generation/service.py`；快速生成前端文件位于 `frontend/src/features/quick-generation/`；VideoTaskPanel位于`frontend/src/features/workspace/`；需求终稿为`docs/电商AI创作平台-首版需求终稿-2026-10-09.md`。

## 需要人工审核的图谱关系

- [ ] 审核全部关系的 source_refs 语义，不仅检查文件存在；结构校验不能证明业务结论。
- [ ] `quick.product → quick.copy → quick.image → quick.video → quick.summary` 的 NEXT_STEP：保留受理、成功+已消费、人工确认条件；不是可以自动执行的路径。
- [ ] `quick.retry REQUIRES quick.failure_frozen` 与 `quick.retry REQUIRES quick.safe_stopped` 为两种可选分支，不能解释成同时满足；停止图片还须服务端新证据，不因名称相似自动建立关系。
- [ ] `quick.failed RESOLVED_BY quick.retry/quick.release`：必须用户选择且服务端成功；释放不是所有故障的万能处理，也不是退款时限承诺。
- [ ] `quick.generate_image REQUIRES quick.materials`：参考图最少数随能力变化，不固化为一张；4张上限有C01政策差异。
- [ ] `quick.confirm_plan REQUIRES quick.new_plan_ready` 仅适用于发生修改后；第一次确认不能被错误要求先编辑。
- [ ] 各 MAY_CAUSE 指向 `quick.blocked` 只说明明确代码阻塞/校验失败。缺少平台或首帧不一定让按钮灰色，必须保留condition。
- [ ] `quick.uncertain/quick.conflict/quick.plan_unread` 对应处理只是核对/重读，不保证立即恢复。
- [ ] 审核关系属性能否在拟用的Neo4j导入程序中完整保留。尚无导入程序/规则执行器，不准省略condition、status或source_refs。

图谱有88个通用节点和106条关系，全部草稿。没有用户、商品实例、账户余额、真实任务编号或业务记录节点。

## 尚未覆盖或未执行验证的场景

- 实际部署版本、真实能力声明、收费配置、真实生成、任务队列、余额变化、超时与补偿均未运行验证。
- Chroma切分/召回/排序、Neo4j查询及联合检索、回答模型质量与延迟没有测试；30题仅准备，不是通过结果。
- 浏览器定位、高亮、手机/键盘可访问性、弹层焦点、动态字段原生校验与多窗口并发未实测。
- 普通专业工作台完整操作、后台管理、所有商品品类字段的逐字段帮助不在本轮核心范围；不可把快速生成的免费次数、字段和限制套用过去。
- 上传逐文件进度、所有文件错误码、磁盘不足/限流的精确用户处理、报价过期批次的全部恢复分支尚需接口级验收。
- 旧版本超限草稿、所有历史文案与图片的完整性、作品删除后来源历史展示、账号停用与在途任务处理、改密跨设备恢复未作端到端覆盖。
- 所有对外人工渠道、身份核验、退款、补偿、生产SLA需另行政策确认，不由知识库补全。

## 建议首批导入文章

以下仅为**人工审核后的候选**，当前正式准入仍为空。编号与文件名一致，可在 [article-index.json](article-index.json)查路径和来源。

- 流程基础：quick-start、quick-product、quick-copy-options、quick-copy-confirm、quick-images、quick-video-frame、quick-video-plan、quick-video-edit、quick-video-supplement、quick-next-step、quick-save-exit、quick-conflict、quick-complete。
- 异常与费用边界：quick-fees、quick-failure、quick-stopped-image、quick-uncertain、quick-recovery；审核C04/C05后再准入相应条目。
- 账号与作品：account-login、account-password、account-credits、account-recharge、works-find、works-download、works-delete、support-demo、support-human。

暂缓：quick-upload（C01）、quick-regeneration（C10）、quick-history（C06）。`planned/`下三篇均不纳入默认可导入资料。对仅限已实现能力的检索过滤必须保留；planned资料可由独立的“功能未开放”评测使用，不能混入默认用户操作检索。

## 发布前签核

- [ ] 确认全部草稿中的事实、适用路由、精确按钮与必填条件。
- [ ] 为每条导入文章/关系填写审核人、日期、依据版本与冲突处理结论。
- [ ] 核对本轮validation-report的来源摘要是否仍对应当前文件；变化后重新检查。
- [ ] 完成30题人工或另行授权的模型评测，所有must_not_claim不得触发。
- [ ] 用单独准入清单导入；不递归导入planned、评测、契约或内部审核说明。
