# 统一 Element Plus 分页（2026-10-21）

用户要求统一分页样式，保留数字页码、上一页、下一页、总数及前往指定页。

## 用户反馈后的本地运行环境修复

首次交付遗漏了本机运行实例检查：前端热更新已生效，但端口 18000 的 Web API 仍运行旧代码。实际 OpenAPI 中四个后台列表尚无 `page` 参数，响应仍是 `CursorPage`，没有 `total`；前端赋值为 undefined 后，Element Plus 的参数检查直接不渲染分页。此前模拟数据与单测通过不能证明运行实例已经更新。

收到用户反馈后，用 ego-browser 在实际登录的后台复现，仅通过项目启动器的进程归属检查重启 Web API，加载新增分页接口；没有重启 Worker 或三个生成服务。随后在真实用户管理、任务与异常、积分管理、操作日志逐页核验接口 200、真实总数、数字页码、前后页和跳页输入。三个多页列表实际执行下一页及输入页码回到首页，全部通过；用户管理仅一页，边界禁用正常。另核验用户积分流水弹窗恢复分页。

后续涉及接口契约的本地改动，必须核对运行中接口版本，并在实际页面做只读验证，再报告运行环境已修复；模拟夹具仅证明对应测试条件下的行为。

## 实现

- 统一入口：`frontend/src/components/ui/UiPagination.vue`，内部为 `ElPagination`，布局为 `total, prev, pager, next, jumper`；沿用项目中文语言包及 V2 暖色。
- 覆盖作品、个人积分流水、后台用户、后台用户流水弹窗、平台流水、任务诊断和操作日志。删除旧后台 `ListPagination` / `useCursorPagination`，清理页面私有分页样式。
- 沿用各页面原每页条数，不添加条数选择器。手机统一换行及控件宽度，保留 44px 交互高度。
- 后台相关列表、账户流水新增可选 `page` 参数和 `NumberedPage` 响应；总数与结果使用相同权限和筛选条件，SQL 直接查询目标页，不遍历全部游标。旧游标调用继续兼容。
- 查询成功后更新页码、总数和已应用筛选；失败保留原页。新筛选从首页查询，越界页收敛至末页，空列表页码为 1。账户流水消费汇总仍覆盖筛选后的完整范围。
- 不替换任务侧栏的“加载更多”，不改变费用、账户写入、任务或作品业务流程。

## 验证

- 后端：`test_numbered_pagination.py`、`test_account_ledger_queries.py`、`test_admin_safe_queries.py`、`test_admin_user_management.py`，61 项通过。覆盖随机页、过滤与所有者范围、空结果、越界、混用分页拒绝、旧游标及已有权限行为。
- 前端：`admin-lists-remediation.spec.ts`、`admin-users-management.spec.ts`、`account-layout.spec.ts`、`works-gallery.spec.ts`，37 项通过。覆盖跨页替换、筛选保留、请求期间禁用、失败保留与重试、未访问页直达及已有业务操作。
- `vue-tsc --noEmit` 通过；Vite 生产打包通过。已有大包体积提示仍存在。
- 本轮相关 Python 文件 Ruff 检查通过；Impeccable 机械检查未发现问题。
- OpenAPI 与 TypeScript 契约已由项目脚本生成。
- ego-browser 使用 TEST_ONLY 合成只读接口及真实 Vue 页面/Element 控件。六个主页面在 1440×1000 与 390×844 下逐页验证下一页、输入跳到第 5 页、末页禁用和回到首页；用户流水弹窗单独验证桌面与手机。另验证请求失败保留首页并可重试、筛选后总数 123→23 且回到首页、空列表总数 0 且前后页禁用，以及 320px 无横向溢出。
- 验证夹具：`frontend/tests/fixtures/pagination.html` / `pagination.ts`。浏览器 TaskSpace 16 已关闭。

## 截图

截图保存在 [pagination-2026-10-21](pagination-2026-10-21/)：`users`、`tasks`、`credits`、`logs`、`account`、`works`、`dialog` 各有桌面和手机版。均为 TEST_ONLY 数据，不代表真实账户或生产联调验收。

本轮完成源码与本地验证；未执行生产部署或数据库写入。
