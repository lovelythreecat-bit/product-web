# T13 核查与人工处置验收

原任务异常进入有负责人、精确政策、期限、待办和持久告警的核查。期限只触发超期处理，不证明失败。管理员按实时会话/角色、明确政策动作、证据、理由和版本处置；审计、任务、核查、唯一结算共同提交。生产D-08/D-09未确认仍关闭。

## 验证及评审状态

- 初版冻结源码完整后端486项通过，无跳过或警告，Ruff及OpenAPI通过；契约、前端类型和构建通过。快照 `006c4bd8e025fdca3d049e4bdcf6fa9adc0555a9db491a96a71aa14a3e97d13b`。
- 独立初审C0/I3/M1：原TaskView原因未更新、管理写路径偏离计划、期限/告警时间无时区。第一轮只修改7个必要契约文件；原失败和初审均保留。
- 修复后主控38项专项、Ruff/OpenAPI，以及契约/类型/构建通过。源码前后相同，快照 `1ce187242b79dc6b868a5caa99b32e0b5df365e271caec47da5d87b834880569`；其余源码逐文件与486项全量版本一致，未把486项记为修复后的再次全量。
- 增量独立评审规格及质量PASS，C0/I0/M1 deferred；三项阻断全部关闭，7文件修复无新增问题，170个raw文件哈希一致、163个未变。最终评审树 `287bd56aa83bae07d8e4cee639f7a2664c035f77`。
- 初审M1记为延后T19：待办游标锚点完成或责任移交后下一页可能422；见执行进度及T19-forward-notes，后台接入和最终评审需关闭或明确裁定。

## 行为与真实数据库证据

管理员跨账户锁按确定用户顺序取得，再权威重查会话、active、撤销、auth_version和数据库role；写接口检查Origin及绑定CSRF。锁外原成果保存/重验后，处置事务再次授权和CAS。无完整durable交付不能人工消费。

原任务恢复沿用task/external/upstream ID、快照及冻结，经原Worker恢复服务处理。恢复终态与核查收尾共同提交，既有任务详情、任务列表、会话历史均返回新的本人处置原因；内部审计保留原诊断依据。两条写路径对齐 `/api/v1/admin/tasks/{id}/investigations` 和 `/resolutions`。期限及告警响应从数据库UTC值转换为带Z的时间，实际HTTP与MySQL时刻比较通过。

人工关闭共用唯一 `settle:<task_id>` 释放账本，再推进MANUALLY_CLOSED。部分成果的manifest/save-item/File固定身份及未形成File的journal/在途身份均保护容量；以file_id/version去重核算最大声明/实际字节，原预留不足则原子补足，容量不足整笔回滚。

任务 `0d5b9281-09d6-4f0e-9b91-75e14b69b610` 在保存1份File后关闭，余额100/0/0、RELEASED，全部固定保存身份的预留由1补足至138字节，文件保持保护。完整原成果人工结算任务 `8e69a94c-b904-4e67-9a43-633c20c0168d` 发布2份File，实际138字节、余额70/0/30。普通NOT_FOUND任务 `215efc92-eaa4-406a-a5fb-75502c5b806d` 仍INVESTIGATING/FROZEN、余额70/30/0，无结算。

两个真实连接并发关闭仅一笔释放和处置记录；审计失败、版本冲突及容量补足不足均回滚。已释放后TERMINAL_LATE仅记录可信冲突与quarantine告警，不逆转终态、补扣或创建新收费意图。

## 交接及限制

新增迁移 `0015_investigations` 承接0014。操作手册位于 `backend/docs/investigations-operations.md`。当前严格schema仅实现operator_review、retain_all、quarantine；TEST_ONLY样本不作为生产默认。持久告警和分页查询已提供，实际值班责任路径接线归运维阶段；本步未发送外部消息。

正式文件回收和容量归还归T17/T22，不能把人工释放积分当作删除磁盘成果。真实Agent仍未联调，不构成生产或上线验收。若生产选择其他迟到/处置语义，需先确认并实现对应严格schema。

完整证据位于 `.agent-runs/2026-10-11-implementation/`：T13-controller-193553、T13-contracts-controller-193555、T13-fix1-controller-195214、T13-fix1-contracts-controller-195218、T13-fix1-source-closure-195216，以及实现初稿/修复、独立初审/增量报告。实现者151项为容量增强前，67项为增强及物理测试根隔离后，均按原版本保留，没有合并为一次测试。
