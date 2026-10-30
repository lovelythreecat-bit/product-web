# README 视觉素材

## 当前展示 · 飞马 UI · 2026-10-30

- Audience：了解项目的电商创作者与准备本地运行的开发者。
- One-sentence value：从一份商品资料出发，在同一个工作台创作文案、图片与视频。
- Primary proof：实际 Vue 页面组件的首页、工作台与快速生成截图，均使用合成测试数据。
- First successful action：先看界面，再按根目录 README 安装依赖、配置本地服务。
- Visual theme：沿用 `DESIGN.md` 的飞马蓝色双主题。浅色背景 `#f3f6fb`、正文 `#182843`、主色 `#1559d6`；深色背景 `#0b1220`、正文 `#eaf1ff`、主色 `#79aaff`；次要文字分别为 `#586b85`、`#a4b5ce`。
- Typography / shape：系统中文无衬线、Markdown 原生标题层级；截图内沿用 8px 控件圆角、14px 面板圆角与 8px 间距基准。
- Motif / composition：同一份商品资料连接文案、图片、视频，以实际界面和自然商品摄影为证据，标题与说明保留为可搜索文字。

`feima-home-light.png`、`feima-home-dark.png` 于 2026-10-30 通过 ego 浏览器重新截图，视口 1440 × 760，来自 `frontend/tests/fixtures/feima-ui.html?theme=light` / `dark`。该测试入口运行实际 Vue 组件、阻止真实写入并提供合成读取数据；图片为浏览器首屏截图，无重绘或生成覆盖。

工作台与快速生成直接复用 `docs/verification/feima-ui-2026-10-30/` 的桌面、手机截图。README 的 `picture` 根据阅读者偏好展示浅色或深色，缺省为浅色，并提供原图链接。Logo 来自用户提供的 `frontend/src/assets/feima-logo-blue.png`；商品图片沿用项目已批准的示例素材，来源见 `frontend/public/homepage/assets-provenance.json`。

本轮不新造装饰性横幅，不生成位图，不加入动画或外部字体。启动命令、能力说明与验证边界保留为 Markdown。下方旧素材保留为历史记录，已从当前 README 展示移除。

## 历史素材 · 2026-10-21

面向了解项目或准备本地运行的开发者与电商创作者。核心表达：围绕商品资料，在映作中完成文案、图片和视频创作。第一步是查看界面，再按根目录 README 配置本地环境。

- `hero.svg`：可编辑的静态 SVG；复用 `frontend/src/assets/brand-mark.svg` 标志及 V2 暖色。背景 `#f8f3ed`、正文 `#322823`、主色 `#a94e32`、次级文字 `#706259`、分隔线 `#e7d9ca`。系统中文无衬线字体，112 / 44 / 32 / 24 字号，24 圆角、2 单位线宽、8 单位间距基准。主题是商品创作顺序，采用留白充足的横向构图，不含外部资源或动画。
- `quick-copy.png`、`quick-images.png`：原样复制 2026-10-21 实际前端组件的合成界面测试截图，分别来自 `.tmp/quick-ui-implementation-20261021/copy-desktop.png` 与 `images-desktop.png`。截图本身保存在此，README 不依赖临时目录。来源说明见[快速生成 UI 验证](../../docs/verification/quick-generation-ui-v1.1-2026-10-21.md)。
- `workspace.png`：原样复制 `docs/verification/screenshots/workspace-redesign-2026-10-17/desktop.png`，见[工作台验证](../../docs/verification/workspace-redesign-2026-10-17.md)。

截图用于展示页面布局与交互结果；商品、文案、余额和费用为测试数据，不是客户案例、真实模型效果证明或生产报价。完整说明、启动命令和流程同时保留在 Markdown，窄屏可点击截图查看原图。
