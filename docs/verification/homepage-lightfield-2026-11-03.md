# 光场首页实施与验证

日期：2026-11-03。用户在浅色视频模块修复后要求“按这一版实现一下”，确认 [光场创作 V1](../design/homepage-bold-2026-11-03/README.md) 为本次实施稿。**已完成本地实现，并于同日 17:28 按用户要求部署。**见[发布与回滚记录](homepage-lightfield-deployment-2026-11-03.md)；下文保留实施阶段验证范围。

## 实施

- `frontend/src/features/site/HomeView.vue`：完整接入大标题、全幅商品舞台、商品到分镜、画廊、视频、玲玲、双工作台、分发和收尾模块。模板／状态由 Vue 管理，图片走已有本地资源与 Vite 构建，不嵌入整张设计稿。
- `homepage.css`：样式限定在 `.site-home`，动画名称加首页前缀，页面外不受组件样式影响。沿用主题偏好；浅色视频使用冷白底、深正文、蓝色操作、浅色图片遮罩及手机文字承托。
- `useHomepageMotion.ts`：CSS 透视＋Canvas 投影光轨、6.5 秒自动轮换、扫描、桌面滚动分镜。手动步骤接管，手机使用点选；支持全局暂停、系统减少动态效果、离屏及后台暂停。Canvas 像素比最高 1.5；卸载取消帧并释放观察器和事件监听，不新增依赖。
- 保留动态品牌名称、登录态和 UserMenu、游客注册／登录、已登录新窗口工作台、客服新窗口入口、授权作品接口及失败重试。删除评审页脚文字和本地硬编码链接。
- 同步 DESIGN.md 与产品设计入口，将用户确认和本次适用范围记为已生效。未修改知识库并行工作。

## 验证结果

| 检查 | 实际结果 |
| --- | --- |
| Vue / TypeScript 类型检查 | `vue-tsc --noEmit` 通过 |
| 生产构建 | `vite build` 通过；仍有既有 UsageView 大于 500 kB 提示 |
| 相关单测 | `site-content.spec.ts`、`user-menu.spec.ts` 共 24 项通过，涵盖空 CMS、授权案例与重试、访客／会员入口、场景 inert、主题减动、轮换暂停与卸载清理 |
| 浏览器 | ego 访问实际 `http://127.0.0.1:15173/`，不是独立提案 |
| 桌面 | 1440×1000 浅／深首屏、创作分镜、浅／深视频模块已核对 |
| 手机 | 390×844 首屏和浅／深视频模块；390px、320px 的 clientWidth 与 scrollWidth 相等，无横向溢出 |
| 交互 | 品类选择、Home / End、滚动到视频步骤、手动场景 inert、玲玲提示、专业介绍切换及注册页跳转实际验证 |
| 减少动态效果 | 模拟系统偏好后按钮禁用并显示“系统已减少动效”，运行中的动画数为 0 |
| 资源与内容 | 检查图片无解码失败，生产首页没有“高保真动效提案”评审文字 |
| 差异检查 | `git diff --check` 通过 |

Vitest 初次因沙箱系统临时目录重命名 EPERM 未启动测试，改用项目 `frontend/node_modules/.test-temp` 作为本次 TEMP/TMP 后，单进程运行通过。未修改系统环境设置或测试配置。现有 Playwright 首页用例选择器已随新页面结构更新；本次实际浏览器验证使用 ego，未另跑该 Playwright 用例。

## 截图

- [桌面浅色](homepage-lightfield-2026-11-03/desktop-light.png)、[桌面深色](homepage-lightfield-2026-11-03/desktop-dark.png)
- [深色创作过程](homepage-lightfield-2026-11-03/creation-dark.png)
- [桌面浅色视频](homepage-lightfield-2026-11-03/film-light.png)、[桌面深色视频](homepage-lightfield-2026-11-03/film-dark.png)
- [手机首页](homepage-lightfield-2026-11-03/mobile-light.png)、[手机浅色视频](homepage-lightfield-2026-11-03/mobile-film-light.png)、[手机深色视频](homepage-lightfield-2026-11-03/mobile-film-dark.png)

画面与营销原句沿用用户确认稿，示例不代表真实视频生成、数字人服务、多店发布等能力已验收。未执行生成、收费、发布或部署，也未把桌面浏览器模拟视口视作真实手机性能验收。
