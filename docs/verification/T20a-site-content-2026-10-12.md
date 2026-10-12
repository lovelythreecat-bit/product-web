# T20a 官网与内容维护代码交付

依首版终稿、T20/T20a brief 与用户代码优先指令完成公开 HomeView、后台 SiteView、实际 API/router/导航、介绍不可变版本/CAS/审计、独立案例授权副本及撤回。新迁移0021_site_content承接0020，TEST_ONLY harness 同步实际 head。

公开介绍只读批准指针，并复核 D07/D11/D12 权威政策；mock 也要求 confirmed，D11 内容引用与正文 SHA 绑定，普通编辑不能批准任意文案。未批准内容保存为草稿，不改变公开版本。案例要求具体来源、归属、独立展示许可、可信非 mock/非 test_only 来源及明确执行规则；原素材/作品的私有权限和归属不变。无真实授权材料保持案例空状态，不把测试夹具用作官网素材。

二进制副本使用独立随机硬盘路径，校验完整长度与摘要后再数据库发布；DB保存文字/版本/摘要/状态。撤回先提交 cleanup_pending 禁止公开读取，再清理公开副本，失败可重复撤回重试。明确 CasePolicy.execution 为 public-copy-v1/persistent_disk/deny_then_delete_copy 和 max_total_bytes，未确认即关闭。16 MiB/20文件为当前实现支持上限，不是生产默认政策。

已执行：后端关键6 passed/4.17s；前端 Vitest关键3 passed；本步 Ruff、OpenAPI/types 和 diff 检查通过。最终主控 contracts/typecheck/build均 exit0、source_unchanged=true，快照 `8b18242989abdf2db86a1622b2ff5fb671a250fa62eee3eb49bbbfb662ccd219`，raw摘要 `157867235e3c5bcfa38fb928c2f12384c3138c8bab3f00c78744df40a47eeaee`，评审产品树 `b99cb8576f3d80cdbfc186c19e3c740763ce646c`。首次迁移字符集及身份夹具失败日志保留，最终结果以 core-3 日志为准。

独立限定评审 Spec PASS、Quality PASS with Minor，C0/I0/M1。M1：不同版本撤回后清理重试默认使用发布版本，会遇409；访问仍关闭。已交T21a补后台撤回版本读取及默认值，原精确版本/政策校验保留。旧T18b/T18c两项Minor继续跟踪。运行接受 R-T20a/T20a 为 revision222/223；会话恢复仅重派未完成且无报告的旧评审，不重复实施或检查。

证据在 `.agent-runs/2026-10-11-implementation/`：T20a-6f5c0659 实施报告、R-T20a-dd23571a 评审报告，core-3/UI-core-1/build-1/Ruff日志，T20a-contracts-controller-060648-summary及对应日志。正向公开/撤回仅为显式TEST_ONLY合成数据库/磁盘夹具的分支验证，未证明真实客户、Agent或合法生产授权。

未验：浏览器/手机/键盘/视觉长矩阵、全后端、并发压力、进程崩溃/journal恢复、外部缓存撤回、真实D11/D12/客户授权与Agent、实际部署/备份恢复。无自动孤儿回收器，已发出的响应不能撤回，生产规则未代签、未对外发布。原T20聚合待验，此记录仅接受代码子步。
