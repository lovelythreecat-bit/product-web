# 首页摄影 V3 正式接入验证

2026-11-03，用户认可图片并要求由新 agent 替换正式首页。实现者 `/root/homepage_v3_integrator`，主控独立验证。仅本地实施，未提交、未部署。

## 结果

- `HomeView.vue` 与 `homepage.css` 接入 7 张 WebP；6 张新成图及 1 张复用输入图，尺寸保持原样，总计 955,946 字节，比来源 PNG 减少 93.4%。
- 手机／美妆／音频用于首屏，鞋服用于画廊；手机广告、细节用于输出与工作台，人物用于静态口播分镜。
- 白底手机仅在创作第 1 步出现一次，标注“上传的商品原图”。工作台不重复白底图，无旧保温杯和通勤图引用。Logo、玲玲、光场动效及业务接口保留。

## 验证

- `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit`：通过。
- `node node_modules/vite/bin/vite.js build`：通过，7 张 WebP 均进入产物。已有 UsageView 分包超过 500 KB 的提示保留。
- `node node_modules/vitest/vitest.mjs run tests/unit/site-content.spec.ts`：11/11 通过。首次沙箱执行因临时缓存 rename EPERM 未收集测试，在常规环境重跑同一命令通过。
- `git diff --check`：本次修改文件通过。
- ego 实际 Vue 页面：1440px 桌面、390px 手机均检查深浅主题；320px 检查无横向溢出。图片全部解码，白底源图数量恒为 1。
- 浏览器实际点击品类、键盘切换、创作步骤 2/3 均正常；未选中场景 inert，工作台两图为广告／细节。截图已人工查看，人物与手机主体可见。
- 现有单测覆盖登录态入口、授权案例隔离、读取失败重试、暂停与减少动效、路由卸载清理。本轮未另行运行 Playwright 套件。

源码检查前后快照一致：`c08a616e5822bcd5399da27409eea0db2c145e870bee818993b552a85f28019a`。范围见 `.agent-runs/homepage-photo-v3-implementation-20261103/plan.json`。

## 预览与限制

[本地首页](http://127.0.0.1:15173/)。本地公开接口当前读取失败，页面保留原有错误与重试提示；未伪造后台品牌或授权案例。此项不影响配图预览，不代表后端业务联调通过。

- [桌面浅色首屏](homepage-photo-v3-implementation-2026-11-03/desktop-light-hero.png)
- [桌面深色全页](homepage-photo-v3-implementation-2026-11-03/desktop-dark-full.png)
- [手机浅色全页](homepage-photo-v3-implementation-2026-11-03/mobile-light-full.png)
- [手机深色全页](homepage-photo-v3-implementation-2026-11-03/mobile-dark-full.png)
- [手机创作输出](homepage-photo-v3-implementation-2026-11-03/mobile-output.png)、[手机人物分镜](homepage-photo-v3-implementation-2026-11-03/mobile-story.png)
- [浏览器检查数据](homepage-photo-v3-implementation-2026-11-03/browser-checks.json)、[交互检查](homepage-photo-v3-implementation-2026-11-03/interaction-checks.json)
