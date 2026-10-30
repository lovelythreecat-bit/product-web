# Logo 名称与主题切换

日期：2026-10-27。范围：用户要求的后台 Logo 名称自定义、全站主题切换。

## 实现

- 管理后台 → 参数配置 → 品牌设置。摘要与右侧编辑抽屉沿用现有控件，取消不保存、禁止 Esc 关闭、关闭恢复焦点。名称去除首尾空白后为 1–24 字符，不接受空白名称及内部控制字符。
- `GET /api/v1/site/brand` 公开只读名称与版本；`PATCH /api/v1/admin/site/brand` 校验 CSRF、有效管理员身份和版本，修改与操作日志同事务提交。版本冲突保留编辑草稿。名称独立于官网介绍的批准流程，不发布介绍草稿或案例。
- `0037_site_brand` 创建 `site_brands` 表，分别初始化 mock、staging、production 三个环境，默认「映作」。部署前执行项目既有 Alembic 升级流程；本轮未修改真实数据库。
- 首页、公共导航、认证展示和浏览器标题使用同一名称。应用启动、身份恢复完成和窗口重新获得焦点时读取；保存当前页面立即更新。迟到的旧后台读取不能覆盖刚保存的新值。长名称省略显示并保留完整 title。
- 公共顶栏切换浅色／深色，默认仍为 V2 暖色浅色。偏好保存在当前浏览器 `yingzuo-theme` 项，跨同源标签页同步，刷新前置恢复；存储被禁止时仍能切换。主题作用于首页、认证、工作台、后台、Element Plus 控件及统计图表。商品图片不反色。

## 检查

- 后端单元测试：名称校验、首尾空白、有效管理员检查、停用／撤销会话拒绝、版本冲突与审计共 9 项通过。
- 前端针对性测试：共 27 项通过，覆盖名称取消／保存／冲突、主题切换／持久化／跨标签页／禁用存储、迟到品牌读取保护，以及受影响后台、图表、官网测试。最后的触发按钮焦点修复后，5 项品牌／主题测试和类型检查再次通过。
- 类型检查与 Vite 生产构建通过。构建仍有运营总览大于 500 kB 的分包提醒。
- OpenAPI 与 TypeScript 契约同步；Ruff、差异空白检查通过；本轮界面检测无发现。
- ego 浏览器验证：后台名称编辑保存与刷新、标题更新、深浅切换、桌面与 390px 手机布局、快速生成商品表单、认证页。截图在同名子目录。
- 浏览器使用仅监听 127.0.0.1 的临时测试数据服务和明确隔离的页面响应夹具，名称示例「星河电商创作」不是品牌定名。认证截图的登录恢复提示来自人为阻断测试身份接口，用于覆盖错误态。
- 补充核对取消不保存、Esc 保持抽屉、24 字符名称在 900px／1440px 不溢出。观察到异步加载使触发按钮失焦后，已在打开前恢复按钮焦点，供共享抽屉捕获；该修复经类型和单元检查，未再次进行浏览器焦点返回复核。验证空间与临时服务均已关闭。
- 真实 HTTP／MySQL 集成用例已添加，但当前未配置 `TEST_DATABASE_URL`，跳过 1 项；本轮不声称真实数据库持久化或生产发布已验收。浏览器表单验证不代替服务端集成验证，未运行真实 AI 生成。

## 截图

- [后台浅色](screenshots/brand-theme-2026-10-27/admin-light.png)
- [后台深色](screenshots/brand-theme-2026-10-27/admin-dark.png)
- [Logo 编辑抽屉](screenshots/brand-theme-2026-10-27/brand-drawer-dark.png)
- [后台手机](screenshots/brand-theme-2026-10-27/admin-mobile-dark.png)
- [首页桌面](screenshots/brand-theme-2026-10-27/home-dark.png) · [首页手机](screenshots/brand-theme-2026-10-27/home-mobile-dark.png)
- [工作台桌面](screenshots/brand-theme-2026-10-27/workspace-dark.png) · [工作台手机](screenshots/brand-theme-2026-10-27/workspace-mobile-dark.png)
- [登录桌面](screenshots/brand-theme-2026-10-27/login-dark.png) · [手机深色](screenshots/brand-theme-2026-10-27/login-mobile-dark.png) · [手机浅色](screenshots/brand-theme-2026-10-27/login-mobile-light.png)
