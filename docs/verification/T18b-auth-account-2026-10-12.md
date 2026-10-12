# T18b 认证、个人资料与本人账户验收

日期：2026-10-12；分支codex/platform-development；基线49007a5f6df8c74deacf60d9f71601c9f2ff658d。仅原T18第二子步骤，创作/作品/SSE与完整F01–08分别归T18c/d。

## 交付与行为

注册/登录、账户及充值说明替换占位，沿用V2奶油米色与陶土橙。账号密码无手机/邮箱前置步骤；密码仅在内存表单和请求使用，卸载清除，不进持久存储、URL和产品日志。注册显式重试保留原key/body，编辑生成新意图，无自动POST重试。公共认证错误保留账号和可见反馈。

初始GET /me恢复身份，真实POST logout撤销会话。受保护401清profile/account，RouterView按身份epoch重建，清旧页面ledger/cursor；跨epoch迟到成功及旧401拒绝为IDENTITY_CHANGED。session/onIdentityChange同步事件供T18c关闭连接与清用户缓存；本步尚无SSE消费者。旧成功/旧401延迟隔离由三项单元复现，真实浏览器覆盖当前401、退出、跨账户，不冒称浏览器额外延迟旧401。

资料默认摘要、统一AppDrawer编辑，昵称1–80字符或null、简介最多500。真实PATCH保存后刷新仍存在；取消/Escape无PATCH并恢复焦点，失败保留输入。两设备合法80/500文本无横向溢出。

GET /account显示可用/冻结/累计消费/累计入账真值，GET /account/ledger使用服务端next_cursor、ledger_id去重；详情显示原before/after及关联ID，有真实task_id才GET本人来源快照。顶栏和账户两充值入口只导航说明与GET，明确首版未开通真实充值，无订单支付加分或mock赠送营销承诺。

## 冻结验证与独立评审

主控在最终245文件冻结源码完整复跑：**14单元 PASS、18 Playwright PASS /1.6分钟**（desktop1440×1000/mobile390×844各9）；contracts:check/typecheck/build均exit0。原11unit/12browser保障保留，新增3身份机制/6实际UI测试。验证前后源码一致，snapshot a76a684dba79a60964d006cbffda9c2a8b3bf0f7e736c246f372d5ed2e7c1178，raw digest d92257ec10aceeff19b426ce4a231c39ea50c00470f7d922a1a86f1cdc634fcf；评审产品树1905f99e049941d1601f953b70cc8fba2bb0d5a3。

18文件改动全部frontend。157后端raw文件与T18a逐项完全相等，沿用T17产品后端585与T18a browser_support4/Ruff/OpenAPI证据；本轮不称新跑585或4。独立Spec PASS / Quality PASS with Minor，**C0/I0/M1**；评审revision174、T18b revision175接受。

M1为AuthForm.vue:28登录网络失败误显示注册重试说明，非阻塞；已记录T21-forward-notes和账本，T21修正文案并供最终整分支评审确认，不改变注册意图或401安全语义。

## 主控本轮真实事实

本轮run_id 9a2d949aac914cc2ae1e246acf709430，自有runtimePID12572实际exitCode0、exitObserved=true、cleanupError=null。Cookie Secure/HttpOnly/SameSite=Lax；证据仅属性，不输出session值。

桌面注册重试账号user aa760217-e58d-45c5-ad24-321cf557b8b2，原key c672da9d-4cb7-4eb5-90a2-4507111ae836，赠送ledger f693ee3c-fd63-4bce-b074-d3d7b3287031；手机user5a25585c-59cb-4713-9315-837229c0cdc5，key205786e3-fbfc-4eab-addd-5709e6153b8b，ledgerbf00c22f-c931-424a-a5b9-59ad785d4e42。各两次真实请求同body、仅一赠送；随后真正换至不同账号、不同流水。网络故障为真实route.fetch后abort，不route.fulfill业务事实。

两设备11成功任务真实冻结/结算产生23流水，UI分页20+3；翻页期间新增第24冻结，旧分页ID仍精确且唯一。桌面新taskdc2bf790-35e2-4bd4-b674-3ca5d97554a5，手机a3ccdc02-fe15-48a5-a6cd-d510057eb8ae，余额均904/8/88、累计1000；完整task/ledger/work/磁盘核验在JSON保存。普通另一账号伪造localStorage角色仍GET原task404。

充值UI账号桌面5bc1c93b-eb23-4110-b3f9-e8fad2ac7b84、手机800a0654-30d1-46fd-8be1-cc56b173c887；两入口前后账户1000/0/0/累计1000、流水和任务JSON严格相同，无mutation。全部数值为明确TEST_ONLY样本，不是生产报价或赠送政策。

## 证据与边界

运行.agent-runs/2026-10-11-implementation保留开发报告T18b-20c6c7e7-2cf6-4e51-acc6-1404ee49f51d.md、独立R-T18b-9c58b378-6082-4ee0-bf81-44c207c1416a.md。开发92产物及主控21浏览器产物全部hash核验，主控证据前缀T18b-frontend-controller-003036、T18b-contracts-controller-003042；账户/重试/流水摘要及runtime receipt另存T18b-controller-*。主控和评审均实际查看两设备长文本账户与来源抽屉最终截图。

原注册占位RED、缺来源入口RED、错误密码401反馈丢失RED和final1旧digest均保留；final2与主控最终结果不混合计数，TS2454诊断不当业务RED。首次主控验证因审批超时/断连未启动，同一授权原机制重试一次后运行成功，无重复harness。主控JSON摘要曾误判calls类型和first/second账号含义，读取真实脚本后修正；解析诊断独立保存，不冒充产品测试失败或改写原事实。

不验收真实支付、生产赠送/品牌政策、找回密码、后台内容授权、创作/作品UI、SSE或完整F01–08。分页新冻结任务作为本run证据保留，未全库清理/FLUSHDB或停止共享服务，所有自有进程已退出。原T18仍待T18c/d聚合。
