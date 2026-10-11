# T18a 前端共享基础验收

日期：2026-10-12。阶段：已确认 T18 的共享视觉、弹层、接口与真实浏览器测试基础。基线 ced2dd467c496a5179c165369aa2cbd7976e4859，分支 codex/platform-development；原 T18 业务页面、SSE消费和 F01–08 仍由 T18b/c/d 完成。

## 交付

Vue3/TypeScript/Vite 共享 V2 奶油米色＋陶土橙语义 tokens、AppShell、AppDialog/AppDrawer、线性SVG图标与六路由占位。页面按产品设计入口保留自己的业务结构。弹层验证 Escape、Tab隔离、焦点恢复、取消初焦、快速重开与手机全屏抽屉。

真实 auth/catalog/conversations/tasks/files/works/account/assist 接口模块消费生成类型；同源安全Cookie、当前CSRF与固定提交key/body，无POST盲重试。实际文件接口是binary body＋display_name query，按既有契约接线；通用FormData不手写boundary。完整SSE消费者归T18c。

测试链为真实HTTPS Vite/API、Worker、HTTP模拟上游、MySQL、Redis与持久磁盘。启动要求 APP_MODE=mock 且 APP_TEST_ONLY=true。随机令牌控制只在loopback测试服务器，隔离账户、任务、stream/group和自身进程。没有产品调试API、真实Agent调用或共享服务停止。

## 冻结验证

主控在最终修复后的冻结源码实际运行：**11单元测试 PASS、12 Playwright PASS /51.5s**（desktop1440×1000、mobile390×844各6），contracts:check/typecheck/build均exit0。验证前后源码一致；快照 d6da40b7e21b55e63ab10462c9b5eae317a2b264fb031fe00c07ed7699a12317，完整235文件raw摘要 cbc724491a7c178493a4262cf1b213207b00b7c19668da7956dcf1473f29ad1b；产品评审树 f26f23b4b12212261087c8581c9b8bab9e5a3128。

157后端文件与初审闭包逐项一致，沿用主控browser_support4项、Ruff/OpenAPI及已验收T17产品后端证据；本轮不冒称重新运行106或585项。初版5单元/10浏览器证据独立保留，未与新结果相加。独立Spec/Quality及限定复评PASS，C0/I0/M0；R-T18a接受revision165，T18a接受revision166。

本轮浏览器真实run_id ba9fca8bad7641a397504f503f175054；安全Cookie属性、实际请求、task/work/ledger ID、一次受理和结算、MySQL/磁盘SHA及异常场景均保留JSON。手机和桌面任务链正常，未知受理、普通NOT_FOUND、保存恢复、部分结果和重复通知不授权重生成或错误释放。API smoke经真实产品模块发请求，不能充当尚未实现的UI用户流程。主控自有runtime PID51012实际exitCode0、exitObserved=true、cleanupError=null。

## 初审两项修复

I-1：AppOverlay页头关闭、取消与只读关闭默认会提交父form，补type=button。真实父form桌面/手机各48种mouse/Enter/Space关闭组合从RED提交48次到GREEN提交0次；显式业务submit仍1次。最终12项浏览器包含该回归，额外JSON reporter2项仅补96次操作事实，不重复计数。

I-2：测试健康请求与shutdown等待无有效总期限，kill后没有等待退出。setup改用共用生命周期函数，健康请求Abort截断剩余总期限；清理先建grace/final期限、取消控制请求、仅停止自有child/连接并实际观察exit后记录。真实随机loopback/Node/Vite六专项保留RED→GREEN，涵盖健康停滞、控制停滞、强杀、Vite报错仍回收child、正常退出、占用连接强关后实际close。首次HTTP2联合类型typecheck失败及修正也保留，未充当业务RED。

## 证据与边界

运行目录 .agent-runs/2026-10-11-implementation 保留原报告、format1、初审、fix1和限定复评。主控最终证据前缀 T18a-fix1-frontend-controller-234535、T18a-fix1-contracts-controller-234550；浏览器产物11文件独立复制并有SHA清单。修复者76项产物清单全部哈希核验，旧7项报告/闭包哈希未变。退出收尾单独保存 evidence/T18a-fix1-controller-runtime-processes.json。

六业务路由仍明确占位。本步不宣称认证/账户/创作/作品完整UI、SSE重连、全部F01–08、真实Agent联调、生产D01–12或上线验收通过。OS强制退出失败会记录cleanupError，不承诺任意操作系统故障下总能终止进程。普通管理员内容授权、慢TCP撤权及运行负载仍按后续阶段处理。
