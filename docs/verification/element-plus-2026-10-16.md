# Element Plus 组件迁移验证

日期：2026-10-16。依据：用户明确要求使用 Element Plus 改造现有项目。

## 完成范围

- 安装并锁定 Element Plus 2.14.7；应用提供中文语言包，组件脚本与样式按需引入。
- 登录/注册、账户、文案/图片/视频工作台、作品与后台的输入、选择和按钮统一使用公共 Element Plus 封装；单选、多选使用库组件。
- 公共对话框/抽屉迁移到 `ElDialog` / `ElDrawer`；账户流水和后台的 9 张表格使用 `ElTable` / `ElTableColumn`。表格保留业务列、行操作与接口行类型。
- 使用现有 V2 暖色 token，不改字段、默认业务值、操作语义或收费流程；桌面工作台保留现有紧凑密度，手机抽屉全屏。
- 保留可自定义文本、空数字输入、布尔选项、必填与范围校验、外置提交按钮的 form 关联、冻结状态及焦点管理。原生文件输入仍用于现有上传。
- 独立只读评审发现选择器未继承 disabled fieldset；已添加祖先禁用状态同步和事件写入保护，并通过组件与真实浏览器回归。媒体首帧单选显式接收工作台冻结状态。
- 更新[公共控件约定](../development/frontend-ui.md)和[产品设计入口](../product-design.md)。

## 最终验证

| 检查 | 结果 |
| --- | --- |
| `vue-tsc --noEmit` | 通过 |
| `vite build` | 通过；按需样式及 Vue/表格分包，无超大 chunk 或循环分包警告 |
| `vitest run` | 28 个文件、177 项通过，退出码 0，无未捕获错误 |
| `playwright test --config=playwright.ui.config.ts` | 12 项通过，桌面 1440×1000、手机 390×844 |
| 既有弹层专项回归 | 4 项通过：Tab/Shift+Tab 焦点隔离、快速重开、固定标题、48 种鼠标/Enter/Space 关闭组合及父表单提交关联；复用入口 `playwright.overlays.config.ts` |

浏览器回归包含：工作台全部文本参数、AI 辅助/撤回、商品类型切换与原资料保留、任务重试及积分释放；后台模型列表/默认模型/服务连接；图片平台与用途联动、首帧显式选择、视频方案确认与补资料；必填阻止保存、数字和布尔值提交、fieldset 冻结/恢复、下拉框 Escape 与弹层 Escape 分级关闭、收费确认取消优先与关闭后焦点恢复。检查页面无整页横向溢出，监听到的 pageerror 为 0。

组件单测使用真实 Element Plus 基础控件，业务页面测试隔离弹层外壳；独立弹层测试与浏览器测试覆盖真实门户和焦点行为。最初发现的测试选择器兼容问题、空白输入显示 `false`、焦点时序和必填代理递归问题均已修复后重跑。

## 实际截图

- [桌面商品编辑抽屉](screenshots/element-plus-2026-10-16-workspace-product-types-desktop.png)
- [手机商品编辑抽屉](screenshots/element-plus-2026-10-16-workspace-product-types-mobile.png)
- [桌面工作台](screenshots/element-plus-2026-10-16-workspace-updates-desktop.png)
- [手机工作台](screenshots/element-plus-2026-10-16-workspace-updates-mobile.png)
- [桌面基础控件](screenshots/element-plus-controls-desktop.png)
- [手机基础控件](screenshots/element-plus-controls-mobile.png)
- [后台服务连接](screenshots/element-plus-2026-10-16-service-connection-drawer-2026-10-15-desktop.png)
- [媒体控件](screenshots/element-plus-2026-10-16-media-controls-desktop.png)

## 边界

浏览器数据是 TEST_ONLY 合成接口或隔离组件数据，不调用真实模型，不代表真实 Agent 联调、生产业务验收或部署。未重新运行依赖数据库/Worker 的全量端到端业务矩阵；本轮没有修改后端、数据库迁移、计费或任务状态机。
