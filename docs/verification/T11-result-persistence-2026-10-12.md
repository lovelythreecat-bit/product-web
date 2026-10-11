# T11 原成果持久化验收

本阶段将可信原成果清单、每个文件的稳定身份与保存记录持久化，支持文件落盘后数据库提交失败或回复不确定时恢复原记录。恢复不重新生成，保存失败期间积分和容量继续保留预留。双成果流程通过实际 TEST_ONLY HTTP、持久归并与文件保存，不以手工构造 DTO 代替。

## 验证与独立审查

- 初版冻结源码完整后端回归414项通过，无跳过或警告；Ruff、OpenAPI检查通过。对应快照 `a575cbb9fd9eeef9b0174bc2b32e3da01b1ea9aaee1d3668adcf5c1326f9b92d`。
- 独立审查发现下载总时限未覆盖TCP/TLS/发送；实际控制流RED复现后，仅修复下载模块及对应测试。
- 修复后主控下载专项26项通过，全后端Ruff、OpenAPI通过；验证前后源码相同，快照 `6287ffdf0e144d810639ee2f3e1745e23d4f2b12d5e786dfaed49e3be60822d9`。逐文件核对确认其余全部产品源码与完整回归版本一致；未将历史414项标为修复后的完整回归。
- 独立增量审查PASS、qualityApproved，Critical/Important/Minor均0。最终15文件raw SHA与评审树 `6845b721c55f7259f62a81e5fc44f4ed58b221f1` 一致。
- 前端及公开契约18文件与T10已通过的契约、类型、构建版本完全相同，本轮复用该闭包证据。
- 实际MySQL新迁移 `0013_result_persistence` 承接0012，结果身份与交付证据禁止UPDATE/DELETE，旧迁移未改写。

## 行为证据

rename后记录提交失败的task `103eaf64-5597-4cd1-bbdc-16e3a5bfb903`，恢复后submit=1、retrieve_original=1；原blob与journal恢复稳定file `446a08f9-7ba5-4c39-bd4f-d2284c15ac2c`，未新增生成。

双成果task `bef4f3e8-1a90-4465-8672-ad46f4bddb61` 形成2份File和task_result保护引用，submit=1、retrieve_original=2，任务仍SAVING/FROZEN，容量仍reserved。提交回复不确定、旧Worker失效及后继原文件恢复、实际格式/完整字节/hash、错误清单、查询故障后原manifest恢复均有定向证据。物理文件锁与数据库fencing分别保护文件和权威记录。

下载逐跳校验精确来源、全部DNS答案、固定数字IP连接和实际peer；TLS使用原hostname与默认安全证书验证。总deadline覆盖DNS、TCP、握手、发送、头、body和重定向。测试复现使用真实request/send控制流，替换底层socket/TLS以检查累计预算。

## 交接与限制

`ResultPersistence.save_original`在发布事务外恢复并物理重验，`verified_delivery(session,task,manifest_id)`在T12同事务重读稳定成果证据。后者不是独立publication证明；T12负责作品/最终消息/账本/状态/事件共同提交、容量按完整总字节核算一次。

当前仅TEST_ONLY mock-v1，固定单成果或经精确spec/D-01/D-04许可的两项模拟成果；生产真实协议和计费政策仍关闭。通用流式下载独立验证，现有worker的小模拟fixture由固定mock适配器获取。Windows目录fsync与断电持久保证未验证，留T22/T24目标部署平台。真实三个业务Agent联调归T23。

完整失败、通过、冻结及独立审查证据保存在 `.agent-runs/2026-10-11-implementation/`：T11-controller-175653、T11-fix1-controller-180830、T11-fix1-source-closure-180805、T11-frontend-closure-175651，以及T11原始/修复与R-T11原始/增量报告。历史失败报告未改写。
