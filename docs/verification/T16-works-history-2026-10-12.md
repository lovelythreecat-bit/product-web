# T16 作品、历史和本人账本

新增本人只读接口 `GET /api/v1/works`、`/works/{id}`、`/account`、`/account/ledger`。作品读取T12原发布集合和最终消息，支持copy/image/video筛选与稳定分页；文件继续由原受保护content接口及Range处理器读取。来源返回固定输入、原报价和政策、素材版本、原任务/会话、积分预留及流水关联。

## 验证状态

主控冻结后完整后端560 passed / 467.23s，无跳过或警告；Ruff、OpenAPI、公开契约、typecheck和build均exit0。源码前后相同，快照 `2452cca761c38b55a30e4e142ca06ab6736c9aaa2eb9e4a998f4890ebfa3ab4b`，完整源码manifest摘要 `3e0a986c08cb6fb6aaa5b92727b9933dc7583c89317a5378ef066536383ba51c`。独立Spec/Quality PASS、C0/I0/M0；最终评审树 `95cf2e5a3a4a8a5545c719dece9ff1f53ff98d00`。本步通过不表示后续UI、生命周期或生产验收。

## 行为与证据

实时本人会话及持久owner校验覆盖任务、会话、消息、商品版本、素材、作品及文件版本；普通管理员也没有内容bypass。外人资源404；新作品/流水外人和未知游标同404。既有历史游标外人和未知均为无内容的422，保留安全兼容契约。新DTO时间明确UTC带Z。

本人账户读接口补齐原计划未接线项，仅新增查询和DTO，不改账本writer/model/迁移；返回三余额、累计入账、分页流水和本人必要冻结去向。无支付或充值加分动作。作品列表不将SAVING或未完整发布的结果作为作品，来源不改变旧输入和费用。

开发者专项11项、受影响旧入口及契约16项通过，Ruff/OpenAPI/contracts/typecheck通过。原任务用真实SQLAlchemy关系fixture初始化，原成果经真实HTTP TEST_ONLY模拟器、持久化服务和ResultPublisher发布，未手造Work/最终消息；新生成经真实报价、上传和受理API。该证据不代表真实供应方联调。

旧任务 `421d20fc-7dae-4d58-9588-395541a78d8d` 与作品 `bc5e846d-b83a-4697-aef0-e9da25b4227d` 保持SUCCEEDED/CONSUMED及原30积分消费。原素材不可用时拒绝受理且不冻结；POST/files补传后重新报价，再以新意图受理任务 `8c15cce4-83ee-455b-ba15-ad3731ffd079`，仅新freeze7，重放不重复冻结。新素材配旧报价仍409。测试余额由940/0/60变为933/7/60，旧作品和旧流水保持。

## 后续边界

没有新迁移，head仍0018_assist_requests。T17实现删除/保留/回收/停用政策，本步素材失效场景不冒称实际删除政策已验收。T18提供真实界面的复制、预览、播放、下载、来源重生成及账户读取；T19提供独立内容授权和后台指定用户账户接口。未知供应商成本不伪造为0。

开发报告及原始证据位于 `.agent-runs/2026-10-11-implementation/reports/T16-b304e1f6-c34f-4334-84f7-16f518abd314.md` 与 `evidence/T16-b304e1f6/`；初始容量不足及测试CSRF缺失失败保留，正确关系fixture后缺路由RED单独记录。

主控证据：T16-controller-212318、T16-contracts-controller-212331；独立报告R-T16-7b9f5abc-ae61-443b-9f08-338d446ec390。原始changed-source-manifest为列表，主控暂存工具首次因格式不匹配未产生修改；另生成保留原hash的等价包装T16-controller-stage-manifest，逐文件核实后暂存，原报告与证据未修改。
