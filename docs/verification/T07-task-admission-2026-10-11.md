# T07 任务受理、不可变快照与事务冻结验收

日期：2026-10-11。分支：`codex/platform-development`。范围为T07受理基础，不代表Worker、完整成果发布、前端业务或生产上线验收。

## 交付

- 本人会话、商品资料不可变版本、任务与持久消息读取；分页游标限制在已授权查询范围，普通管理员不默认取得用户内容权限。
- 当前账号与会话鉴权后，按user+key及完整规范化请求先查幂等。同体返回原任务和原报价，调价或下架亦然；异体409。新键才重新检查报价、精确政策、素材、积分、并发及容量。
- 单一MySQL事务固定输入、Agent、规格、报价和政策快照，并写任务、积分冻结/流水、全部结果容量预留、素材保护引用、消息、初始状态事件、Outbox和durable event；提交前没有上游或Redis调用。
- 显式检查实际磁盘余量；服务端上界估算绑定规格与D-10版本。生产配置没有模拟估算默认值。
- 积分冻结/流水关联真实任务的账户复合外键；任务身份和输入快照不可覆盖，历史记录append-only。Outbox与durable event写入者不自行commit，为后续调度和事件流提供事务基础。
- 新迁移`0009_tasks_admission`承接`0008_storage_many_files`，任何DDL前拒绝历史孤儿任务引用。

## 证据与评审

真实业务RED为尚未实现的会话POST返回404；冻结专项37 PASS、9 deselected，实际退出码0。主控全后端**235 PASS，无skip**；Ruff、OpenAPI、contracts、TypeScript类型检查及前端构建全部退出0。测试前后源码快照一致：

`44ad0e259969298d439c578c88156ceccf032e3d3de0a801c6c03202e1c32d3f`

独立评审R-T07给出spec PASS、qualityApproved=true，Critical/Important/Minor均0；具体检查了鉴权、容量锁、目录锁和精确政策接口。冻结25个源码文件已全部纳入暂存评审包，评审tree为`ba3b4237aa30ce40feaca6b319a90271753b0f6a`。正式运行账本revision63已验收T07/R-T07。

后续测试使用隔离schema`ecommerce_ai_test_t07_20261011`，主控只读核验head0009。旧`ecommerce_ai_test`保持head0008、10条冻结记录，账户余额全部守恒；没有删除历史或为旧夹具伪造legacy任务。当前旧表行摘要已保存用于以后比较，未声称存在未采集的历史逐行摘要。

运行证据位于`.agent-runs/2026-10-11-implementation/`：`reports/T07-9fb9d72c-54f2-4cb5-a148-ebed98acfceb.md`、`reports/R-T07-47fcb98d-9b98-4224-ad71-fa58d778d65f.md`、`evidence/T07-controller-150127-summary.json`、`evidence/T07-contracts-controller-150317-summary.json`、`evidence/T07-controller-databases.json`和冻结/RED/GREEN记录。

## 后续责任

T08补数据库租约、fencing/CAS、Redis消费和按阶段恢复；T09/T10处理上游证据与查询；T11/T12恢复原成果并完整发布结算；T14提供鉴权事件流；T17负责生命周期；T18实现业务页面；T23依据三个真实Agent项目进行封装联调。未确认生产政策仍关闭。
