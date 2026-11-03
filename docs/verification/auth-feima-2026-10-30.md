# 登录注册飞马视觉实施验证 · 2026-10-30

依据：用户确认 `docs/design/auth-feima-2026-10-30/approved-design.png` 并要求按稿修改正式页面。

## 实施

- AuthForm：共享双栏、400px 表单、48px 输入／按钮、留白与链接层级；保留原字段、验证、状态、幂等与跳转逻辑。
- AuthShowcase：无文字的浅色／深色商品背景，真实 HTML 标题和能力条；标记创作示例，加载失败回退原品牌展示。
- AppShell：仅 `.app-shell--auth` 使用居中一体式顶栏与内容外壳；修复继承全局 shell-body 最小高度导致桌面能力条溢出首屏的问题。手机保持顶栏和单列表单。
- 商品 WebP 随模块导入进入生产构建，104,546 / 115,796 字节；不依赖 DEV，也不扩大 public 目录发布范围。后台品牌名称继续生效。

## 验证结果

- `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit`：通过。
- `node node_modules/vite/bin/vite.js build`：通过；生产输出含两张哈希 WebP。既有 UsageView 大 chunk 警告仍在，本次无修改。
- `node node_modules/vitest/vitest.mjs run tests/unit/brand-theme.spec.ts`：5/5 通过。初次沙箱临时目录 rename EPERM，改用项目 node_modules/.cache/auth-verification 作为 TEMP/TMP 后通过。
- `impeccable detect --json`：本次三个 Vue 文件未报告机械样式问题；随后仅修复已识别的认证外壳 min-height。
- `git diff --check`：通过。
- Ego 浏览器使用实际 Vite 生产构建，1440×960 和 390×844 各覆盖登录／注册、浅色／深色，共 8 张最终截图；无横向溢出，提交按钮均 48px。桌面外壳底部 y=920，能力条底部 y=919，完整位于视口内。
- 1000×800 表单宽约 371px，无横向溢出；320px 注册错误状态无横向溢出。手机隐藏装饰展示区。
- 空提交不发请求，显示账号／密码校验；确认密码不一致提示正常；提交期间全部输入和按钮禁用；失败重试沿用相同注册 request_key。
- 改密提示仍在登录表单内；账号 Tab 后到密码；图片错误回退品牌展示，表单保持可用。
- 独立完稿审阅：ship；确认最终桌面能力条完整、双主题及手机适配符合确认稿，未发现字段／提交语义变化。共享规范复核无需修改 DESIGN.md 或 sidecar。

## 证据与边界

截图和机器结果位于 `auth-feima-2026-10-30/`：`{login,register}-{light,dark}-{desktop,mobile}.png` 为最终截图，`layout-checks.json`、`form-checks.json`、`additional-checks.json` 为结果。`ego-01.mjs` 至 `ego-08.mjs` 为本次可追踪操作，最终截图由第 07 轮生成。

本地没有运行认证后端。主视觉和表单提交检查使用仅浏览器会话内的测试 fetch：未登录接口返回 401，品牌示例为“飞马”，认证提交返回 401；未写入正式代码、未创建真实账号。`login-light-desktop-initial.png` 是首次未注入测试接口的中间图，不是最终视觉。改密提示截图显示本地后端不可达时的真实恢复登录错误，故只证明提示位置。本次不宣称真实登录／注册／计费全链路通过，不包含生产部署。

环境：系统 pnpm shim 路径损坏，验证直接使用仓库已安装的 Node CLI；未改包管理器或依赖。预览服务因沙箱回环访问受限，经工具批准在主机启动，仅监听 127.0.0.1:15173。Ego 提示有新版，本次未升级。
