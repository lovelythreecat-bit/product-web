# 快速生成 UI V1.1 实施与验证

2026-10-21。依据：用户确认 `docs/design/quick-generation-ui-2026-10-21/` 当前 V1.1，并要求“按这个样式新开agent落实一下”。批准稿的 HTML/CSS/JS 未更改，仅更新 README 批准状态。正式实现留在当前工作区，未提交、未发布，未运行真实收费生成或写入真实商品。

## 范围与实现

- 仅快速生成内部商品、文案、图片、视频、完成汇总与相关弹层。公共顶栏、任务侧栏、普通单项任务与其他页面保留现状。
- 标题辅助说明同行，步骤无二行小字，成功阶段取消重复说明条；底部保留主要操作与必要费用。文案白色编辑纸使用暖灰画布，桌面两列、1700px 起三列、手机单列。原始文案任务以固定列展示名称/状态/详情，原始成果在详情中可读、复制，并保留读取失败的重试。
- 商品使用真实 `materials`，桌面当前图与缩略图，手机紧凑网格点图预览；连续前后浏览，移除当前图后就近回退，移除全部后关闭预览。多选和拖入均校验类型与 20 张上限，顺序上传，失败停止后续上传；上传中、锁定、冲突、未明请求与历史只读限制仍有效。
- 图片按真实任务分组、完整预览，三张详情图不显示单图标题，未新增单图字段。完成流程仍只读。
- 快速生成视频方案抽屉提供编辑入口，编辑保留保存并新增确认。修改后先使用现有 `/video/plan-revisions` 命令保存，再 GET 原任务读取新方案；仅接受 `awaiting_confirmation`、完整文档、整数新版本、`plan.plan_version === head_plan_version` 且大于被修订版本的方案。之后进入现有居中确认，确认不重复收费。取消返回已保存编辑内容；异步规划、读取失败、修订结果不明不确认旧版，关闭抽屉后仍有重新读取入口。已读新版本保留，父页面旧状态不会覆盖。原命令重试沿用原幂等键；普通任务不启用新增交互。

## 本轮文件

正式源码：

- `frontend/src/features/quick-generation/QuickGenerationView.vue`
- `frontend/src/features/quick-generation/QuickProductSummary.vue`
- `frontend/src/features/quick-generation/useQuickGeneration.ts`
- `frontend/src/features/quick-generation/quick-generation.css`
- `frontend/src/features/workspace/VideoTaskPanel.vue`
- `frontend/src/components/TaskCard.vue`

测试与验证入口：`frontend/tests/unit/quick-product-summary.spec.ts`、`media-workspace.spec.ts`、`task-card-retry.spec.ts`；`frontend/tests/e2e/quick-generation.spec.ts` 更新旧“奇数最后卡片跨整行”布局期望、旧商品编辑抽屉选择器与旧只读标题文案，商品按已批准内联编辑→保存新版本→重新加载验证，mock 与创建批次输入保留新版本绑定；`frontend/tests/fixtures/quick-ui.html` 与 `quick-ui.ts` 为新增合成界面入口。

文档：本记录、`docs/product-design.md` 和批准稿 README。原工作区文件基线位于 `.tmp/quick-ui-implementation-20261021/baseline/`，保留相对路径；本轮差异和文件清单位于同目录 `implementation.diff`、`manifest.json`。基线包含当时已有的未提交修改，不以 HEAD 差异代替本轮变更。

## 命令验证

工作目录 `F:/Work/电商/web/frontend`。机器 `pnpm` shim 指向缺失 corepack 文件，因此直接调用已安装本地 Node 入口。Windows sandbox 默认临时目录曾发生 Vitest 缓存 rename EPERM，改为本工作区临时目录后正常执行：

```powershell
$env:TEMP = (Resolve-Path ../.tmp/quick-ui-implementation-20261021/runtime).Path
$env:TMP = $env:TEMP
node node_modules/vitest/vitest.mjs run tests/unit/quick-product-summary.spec.ts tests/unit/media-workspace.spec.ts tests/unit/quick-generation.spec.ts tests/unit/task-card-retry.spec.ts
node node_modules/vue-tsc/bin/vue-tsc.js --noEmit
node node_modules/vite/bin/vite.js build
```

相关单测 4 文件、93 项通过，退出码 0。覆盖连续预览/当前图移除、拖入限制、历史只读、修订后新版本确认、取消返回、修订不明原键重试、读取失败不确认旧版、关抽屉后恢复、新版不被旧父状态覆盖、原始成果读取重试。日志：`vitest-related-final.log`。最后补强完整方案文档校验后，视频相关 21 项再次通过，退出码 0：`vitest-media-final.log`。类型检查退出码 0：`typecheck.log`。构建退出码 0：`build-final.log`，仅现有大于 500 kB chunk 提示。

另执行 `node node_modules/vitest/vitest.mjs run`，退出码 1：47 文件中 44 通过、3 失败；386 项中 377 通过、9 失败。完整日志 `vitest-full.log`。失败项如下，未扩大本轮范围修复，也不声明全量通过：

| 文件 | 失败用例 |
| --- | --- |
| `runtime-lifecycle.spec.ts` | `health deadline aborts a connection stalled before TLS response`；`stalled shutdown control cannot postpone the exit deadline`；`cooperative control exits normally without forced termination`；`occupied owned server is force-closed and awaited within the final deadline` |
| `user-identity-display.spec.ts` | `shows accounts in user lists, details and recipient options without UUID fallbacks`；`keeps an unknown pending grant inspectable without exposing its internal recipient`；`resolves audit actors and account-status objects to accounts, including details` |
| `user-pages-remediation.spec.ts` | `renders real projected work and conversation names and keeps deletion available for video`；`work filters preserve API kinds and source details avoid raw JSON; deletion remains policy-gated` |

上述失败涉及本地网络 EACCES/进程控制时限及账户、作品旧 mock/API 期望，本轮没有修改对应源码；根代理亦检查了日志。未执行修改前全量对照，故不以本记录证明全部失败的历史起点。根代理另使用 `.tmp/quick-ui-implementation-20261021/playwright-root.config.mjs` 复用 15173，在沙箱外 Edge 运行 API 全拦截的无收费 Playwright 回归，最终 **6/6 覆盖通过（分轮）**：前两用例桌面/手机共 4 项通过；修正原有商品内联编辑、标签关闭、取消恢复与只读标题的过时测试操作后，第三用例桌面 26.4s、手机 26.3s 均退出码 0。复跑命令为 `node node_modules/@playwright/test/cli.js test --config=../.tmp/quick-ui-implementation-20261021/playwright-root.config.mjs --project=desktop --grep="keeps explicit confirmations" --timeout=90000`，手机将 project 改为 `mobile`。保留新产品版本保存/刷新恢复、精确费用二次确认、免费次数、11 次受理、5 张图片、方案确认与历史只读断言；没有修改生产取消语义，也未连接真实后端或发起真实收费。

## 浏览器核验

使用 ego 浏览器空间 4、p1，真实公共组件与真实快速生成组件挂载在合成 fixture。入口：`http://127.0.0.1:15173/tests/fixtures/quick-ui.html?step=1`。`step=2/3/4/5` 为文案/图片/视频方案/完成只读；`&frames=1` 首帧选择、`&empty=1` 空参考图、`&empty-results=1` 无图片成果、`&failure=1` 图片部分失败、`&loading=1` 文案处理中。所有 API fetch 在内存回答，未知写入拒绝；图片为 TEST_ONLY SVG，未连接真实生成服务。仅是开发验证入口，不编入正式应用入口。

实施代理检查桌面 1440×1000 商品、文案、图片均无整页横向溢出，footer bottom=975；手机 390×844 商品与文案单列自然滚动、无横向溢出。桌面缩略图切换并连续预览到第 3/4 张；手机编辑抽屉全屏且保存/确认可见。浏览器编辑后观察修订请求绑定版本 3，GET 后居中确认显示版本 4，尚未点击真实出片。根代理独立核验：桌面原始任务 7 行状态 x 均 1149；手机 7 行状态 x 均 203；两者均无整页横向溢出；手机任务详情抽屉动画结束 left=0、width=390；三张详情图内无 h3/h4/figcaption 标题。根代理另确认 390px 手机视频首帧底部预计 10 积分可见、无横溢；完成只读页三成果分区无重新生成/编辑方案/确认生成等变更按钮。

截图位于 `.tmp/quick-ui-implementation-20261021/`：`product-desktop.png`、`copy-desktop.png`、`images-desktop.png`、`product-mobile.png`、`copy-mobile.png`、`edit-plan-mobile.png`、`confirm-plan-mobile.png`；根代理补充 `root-originals-desktop.png`、`root-task-mobile.png`、`root-details-desktop.png`、`root-completed-desktop.png`。`edit-plan-desktop.png` 捕获于抽屉进入动画，不能作为最终边界尺寸证据；手机及根代理动画结束后的证据有效。

独立代码评审发现并已修复：新方案被旧父状态覆盖、手机费用被隐藏、图片/汇总 scope prop 遗漏、compact 原始成果缺读取重试、关闭待更新抽屉后缺重读入口。最终只读复核无未决实质问题。

## 验证边界

这是本地前端实现与合成状态验证；未验证真实 Agent、真实收费、生产上传与真实视频播放，不代表发布或生产验收。公共手机外壳保留原布局。图片长宽比和实际文案长度随真实成果变化，预览继续使用完整作品。全量测试 9 项失败保留上述记录。
