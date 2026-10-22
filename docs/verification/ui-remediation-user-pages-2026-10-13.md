# 用户页面整改核对（2026-10-13）

状态：限定代码整改完成，仍有原型/真实接口差异待用户决策；不代表全站、真实 Agent 或生产验收。

## 范围与依据

执行者 U；run_id `5fe06c07-2913-4408-bae2-ba7cd7568202`；attempt `75e87ccb-3bd1-4a30-8564-b1b1ffe85e6f`。依据 AGENTS.md、ui-remediation-manual、product-design、首版需求及 V2 visual-reference。主控已加载 impeccable context，本执行者读取 operate/craft-floor。仅修改 AuthForm、AccountView、RechargeInfoView、WorksView 及定向单测；未改服务端、接口、会话状态和共享组件。首页及共享 shell/ResultViewer 由其他执行者负责。

## 实际整改

| 页面 | 原型依据 | 原实现差异 | 当前结果 |
| --- | --- | --- | --- |
| 登录/注册 | views.js auth；app.js auth-form | 注册无确认密码；无双入口切换；标题不同 | 恢复“欢迎回来/注册体验”、登录注册切换、确认密码与两次一致校验；确认值不发送/存储；同一注册意图重试仍复用 request_key |
| 个人中心 | app.js account/editProfile | 三段纵向面板、无账号详情/页面退出入口 | 桌面资料+积分两列，手机单列；摘要编辑抽屉保留取消不保存；已有真实账号字段放只读抽屉；退出调用既有服务 |
| 积分 | app.js ledgerDetail/account | 卡片流水；日期缺失于详情；关联任务未在列表显示 | 三余额、流水表、详情抽屉含时间/前后余额；从真实 getTask 获取 conversation_id 后进入来源会话 |
| 充值 | app.js recharge | 三余额大块、标题/返回入口不同 | 恢复“充值积分”、可用/冻结、未开放提示、后续微信/支付宝及比例档位退款说明、返回工作台；仅读取余额 |
| 作品 | app.js worksPage/task-detail/delete-work | 下拉筛选、删除藏详情、快照/报价/素材裸 JSON | 按钮分类型筛选；列表调用共享 compact ResultViewer；更多→删除确认；只读任务来源抽屉、中文快照/金额、素材状态和账本关联，去除 JSON |

## 尚未对齐，不能标为通过

| 编号 | 原型位置/要求 | 真实限制或保留差异 | 影响/后续 |
| --- | --- | --- | --- |
| U-01 | profileFields：店铺名称、主营类目、联系邮箱、联系电话 | ProfileView/ProfileUpdate 无相应字段；没有添加假字段或将其写入 bio | 缺完整资料摘要与编辑；需要用户给改造计划和服务端契约 |
| U-02 | account-detail：状态、注册时间、最近登录 | 当前 ProfileView 仅 user_id/account/nickname/bio/role | 账号详情只展示真实已有三项；缺项待契约，不伪造正常状态 |
| U-03 | 原型昵称必填40、简介300；密码8为演示规则 | 当前真实昵称可空80、简介500、密码10–128 | 保留已有真实校验与已存资料；不以原型演示规则覆盖；约束统一待决定 |
| U-04 | 原型作品 name、会话 title | WorkView 无 name 或 conversation title | 显示“文案/图片/视频作品”和来源会话链接，未假造标题；完整名称需契约/既有汇总查询计划 |
| U-05 | 原型动态参数中文名/选项，任务详情事件和完整版本快照 | WorkSource 仅参数对象，没有提交时中文字段/选项元数据和事件轨迹 | 已知字段中文映射，未知字段只用“其他资料 n”，不裸露key；复杂值提示保留原记录；不能声称完整动态语义对齐。原 JSON 展示的版本信息应后续按原型完善为中文明细 |
| U-06 | 原型重新生成直接打开重新收费确认 | 既有真实流程读取作品+商品版本→创建会话草稿→工作台重新报价确认 | 本次未重写可靠任务提交流程；原型流程仍有差异，需主控/用户计划，不得称完全一致 |
| U-07 | 原型示例删除仅移出演示列表 | 真实 D-09 决定删除/链接可访问，当前无版本时禁用确认 | 保留服务端门槛，不能按原型无条件删除；未测试真实删除 |
| U-08 | 原型注册按钮带“演示”及演示积分说明 | 真实按钮保留“创建账号/登录”，无模拟赠送数值 | 不把演示会话文案带入真实身份流程 |

未知字段没有丢弃或修改源数据，仅改变展示；仍需后续提交时显示元数据支持精确还原。

## 验证证据

证据根：`.agent-runs/2026-10-13-ui-remediation/evidence/U-75e87ccb-3bd1-4a30-8564-b1b1ffe85e6f-`。

- `unit.txt`：5项定向单测通过（确认密码拦截+同注册意图重试、登录真实校验、资料取消恢复、作品筛选/来源/政策禁删、账本来源读取后导航）。
- `typecheck.txt`：早期 vue-tsc --noEmit 通过；最终全局检查因并行首页 HomeView.vue 的第32/63/87行 content.value.content 可能为 null 报错，U文件未报告类型错误。此问题已交主控，不冒称最终全局通过。指定文件 git diff --check 无错误。
- `prototype-clicks.txt`：通过 Playwright 系统 Chrome 实际点击原型注册、资料编辑、账号详情、流水详情、充值、作品预览、任务详情、删除确认，保存原型文本/字段。Chrome DevTools 连接失败；Playwright默认下载浏览器不存在，切换已有 channel chrome 成功，未安装软件。
- `browser-script.txt`：可重跑脚本。`browser-results.txt` 保存 API 夹具和检查结果；真实前端 `http://127.0.0.1:15173`，API route 为合成夹具。桌面1440×1000与手机390×844检查账户/充值/作品/注册；最终均无整页横向溢出，已检查页面 pageerror 为0。编辑取消、详情展开、缺删除政策禁用已点击。
- 图片：`desktop|mobile-account.png`、`recharge.png`、`works.png`、`register.png`、`ledger.png`、`work-source.png`。第一轮发现账户grid item自动最小宽度撑宽手机，补 min-width:0 后第二轮通过。人工目视查看桌面账户/作品/注册及手机账户/注册/来源抽屉；截图为夹具呈现，不是真实账户、Agent产出或全页视觉签收。
- 未运行真实端到端注册/账本/删除/重新生成，未验图片视频实际下载和完整键盘焦点回路，未做全部原型交互及后端回归。共享弹层与ResultViewer由主控归总其验证。

## 现有 E2E 跟随项（已通知主控）

注册需额外填写“确认密码”，提交按钮仍创建账号/登录。充值标题改“充值积分”、提示“在线充值暂未开放”。账户列表选择器改 `.ledger-table tbody tr`，查看流水aria-label不变；来源改“查看来源会话”并导航到实际conversation_id。作品下拉改role group按钮，作品详情按钮改“任务详情”，删除在“更多”中，确认文案“确认删除”。账户内部增加退出入口，避免与header不加scope的重名选择器。

## 后台下一阶段只读差异摘要

原型8模块，当前6路由：用户+积分、任务+用量、Agent+规格合并；规格与价格又拆离原型联合操作。用户页缺关键词搜索/店铺/最近登录/任务数及新增编辑重置删除流程，多数涉及DTO或未确认政策，须逐项判定。Agent表有kind/mode/TEST_ONLY/delivery_kind，抽屉有政策/字段/组合JSON，与原型配置表差异明显。任务查询缺原型Agent筛选/任务关键词，diagnostic_code和核查pretty JSON外露。审计action及changes JSON未中文化。此次未修改后台；主控已确认下一阶段按既定整改恢复8模块；接口缺字段/操作单列。应在不变更权限、幂等、版本与证据校验的前提下按原型核对。
