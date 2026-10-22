# 登录与注册重设计验证

日期：2026-10-21。状态：用户已确认双栏设计方向，已完成本地实现与限定验证；未部署。

## 实现

- `AuthForm.vue`：桌面 55/45 双栏、最大 400px 表单；账号与密码提示同行；48px 输入框和提交按钮，保留字段关联、行内错误、自动填充及原认证逻辑。提交中展示加载并禁用。
- `AuthShowcase.vue`：沿用 V2 色板、既有品牌与商品创作示意。开发环境显示已有示例图并标注示意；生产构建或图片加载失败显示品牌。没有改变 `copyPublicDir:false` 或案例授权。
- `LoginView.vue`：改密成功提示通过插槽放在表单页签下方。
- `AppShell.vue`：认证路由专用外壳样式，以 flex 适应顶栏真实高度；其他路由不应用。手机保留公共顶栏和原入口。
- `tests/fixtures/auth-ui.html` / `auth-ui.ts`：真实页面、公共组件及外壳的独立预览；hash 路由，fetch 统一模拟延迟 503，避免真实账户写入或退出已有会话。未加入生产入口。

## 检查结果

- 类型检查：`node node_modules/vue-tsc/bin/vue-tsc.js --noEmit` 通过。
- 生产构建：`node node_modules/vite/bin/vite.js build` 通过；运营总览包仍有 >500 kB 提示，本轮未调整。
- `session.test.ts` 与 `password-change.spec.ts`：14 项通过。
- `user-pages-remediation.spec.ts` 的两项认证测试：注册确认密码拦截与同请求重试、登录密码长度限制通过。该文件完整运行另有两项“我的作品”断言失败（作品删除状态与列表分页参数不匹配）；本轮未修改 WorksView 或相关测试，不将整文件报告为通过。
- 测试启动首先受 pnpm shim 路径错误及系统临时目录 rename EPERM 影响；改为直接调用本地 Node CLI，并将 TEMP/TMP 指向项目 `.tmp/auth-redesign-20261021/test-temp` 后正常运行。Vue 静态公共图片路径在 Vitest 中被当成文件 URL，已参照首页改为动态字符串绑定。
- impeccable 检查本轮三个认证组件：无机械规则发现。
- 独立专项静态评审：未发现本轮新增阻断问题。

## Ego 浏览器验证

使用独立测试入口渲染实际页面，没有清理 cookies、退出用户会话或创建真实账户。

- 1440×960：登录、注册双栏和完整商品示意；表单宽度 400px。
- 390×844、320×568：单列表单，展示区隐藏；输入框和主按钮 48px。
- 额外测量 768px、1024px：无整页横向溢出；768px 表单 400px，1024px 约335px。
- 实际点击注册页签；密码不一致在确认字段下方报错；匹配后提交展示忙碌并禁用全部输入和提交按钮；503 失败后保留账号密码并展示原失败提示。
- 键盘 Tab 从账号进入密码；密码修改成功提示位于表单内部。
- 触发图片 error 后品牌回退正常显示。生产构建使用同一回退布局。
- 上述为本地 UI 与模拟失败验证，未重新执行真实服务注册/登录端到端流程。

## 截图

- [桌面登录](screenshots/auth-redesign-2026-10-21/login-desktop.png)
- [桌面注册](screenshots/auth-redesign-2026-10-21/register-desktop.png)
- [手机注册](screenshots/auth-redesign-2026-10-21/register-mobile.png)
- [手机登录与改密提示](screenshots/auth-redesign-2026-10-21/login-mobile-notice.png)
- [320px 登录](screenshots/auth-redesign-2026-10-21/login-small-mobile.png)

截图来自本地开发预览，商品图是示意素材。
