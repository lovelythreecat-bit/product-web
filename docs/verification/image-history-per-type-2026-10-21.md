# 图片历史版本按类型查看 · 2026-10-21

用户已确认：历史版本是每种图片重新生成之前的版本，不能汇总当前全部图片。

## 实现

- 将图片区顶部统一入口移到各类图片标题旁，图片阶段与完成汇总均提供相同入口。
- 只读取选中类型在当前批次及之前的已提交成功任务，排除当前任务及其重试后继、其他图片类型、未提交批次和重复任务引用，旧版本由新到旧显示。
- 无旧版本显示“暂无历史版本”；详情图按原有整组 3 张保存、预览和下载。
- 保留现有只读抽屉、居中预览及生成费用确认；使用后端已保存的批次和成果，无数据迁移。
- 相同任务轮询刷新不关闭抽屉，切换流程或当前任务时关闭。

## 自动检查

- 新旧语义回归先确认失败，再实现修复；轮询关闭问题同样先复现失败再修复。
- `node node_modules/vitest/vitest.mjs run tests/unit/quick-image-history.spec.ts tests/unit/quick-generation.spec.ts`：57 项通过。
- `vue-tsc --noEmit`：通过。
- 全量前端单测：49 个文件，389 项通过、9 项失败。失败涉及以下未修改模块，不将全量结果标为通过：
  - `runtime-lifecycle.spec.ts`：`health deadline aborts a connection stalled before TLS response`、`stalled shutdown control cannot postpone the exit deadline`、`cooperative control exits normally without forced termination`、`occupied owned server is force-closed and awaited within the final deadline`。包含本地连接 `EACCES`、请求未抵达与退出信号断言失败。
  - `user-identity-display.spec.ts`：`shows accounts in user lists, details and recipient options without UUID fallbacks`、`keeps an unknown pending grant inspectable without exposing its internal recipient`、`resolves audit actors and account-status objects to accounts, including details`。账户展示预期与实际结果不符，部分页面显示网络连接失败。
  - `user-pages-remediation.spec.ts`：`renders real projected work and conversation names and keeps deletion available for video`、`work filters preserve API kinds and source details avoid raw JSON; deletion remains policy-gated`。删除入口及分页查询参数预期不符。
- 本机 pnpm shim 路径失效，因此直接使用已安装的 Vitest / vue-tsc；Vitest 临时目录改为工作区 `.tmp`，避开系统临时目录的重命名权限问题。

## 浏览器验证

使用 ego 浏览器与现有 `TEST_ONLY` 本地验证页，不产生真实生成费用。

- 图片阶段：主图、详情图、长图分别有历史入口；详情图只显示旧详情任务与 3 个下载入口。
- 主图无旧版本时抽屉显示空状态，历史任务数为 0；关闭详情图历史后焦点回到对应入口。
- 完成汇总在 390 × 844 手机视口仍仅显示旧详情任务、3 个下载入口，无横向溢出；截图已人工查看，抽屉内容独立滚动，关闭按钮可见。
- 截图：[桌面](screenshots/image-history-per-type-desktop.png)、[手机完成汇总](screenshots/image-history-per-type-mobile.png)。

本记录不代表真实 Agent 生成、生产发布或全站验收。
