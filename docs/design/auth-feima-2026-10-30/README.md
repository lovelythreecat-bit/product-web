# 飞马登录与注册 · 2026-10-30

用户确认本目录 `approved-design.png` 后要求修改正式页面。沿用飞马蓝色双主题，桌面 55% 商品展示／45% 表单，共用品牌顶栏；手机及 <=800px 仅展示顶栏和单列表单。标题、切换链接、账号、密码、确认密码、字符限制、错误及改密提示维持原有语义。

正式实现：`frontend/src/features/auth/AuthForm.vue`、`AuthShowcase.vue`、`frontend/src/components/AppShell.vue`。认证外壳限定样式，不改变其他页面布局。表单最大宽 400px，输入和提交按钮高 48px；已有 Element Plus、主题偏好、后台配置品牌名和认证逻辑保留。

## 商品素材

- `frontend/src/assets/auth/product-stage-light.webp`
- `frontend/src/assets/auth/product-stage-dark.webp`

使用内置 imagegen 工具，以确认稿制作无文字的独立商品背景，再以同构图生成深色版本。FFmpeg 仅作 WebP 格式压缩（quality 86），未经裁剪或重新绘制。每张约 100–115 KiB，通过模块 import 进入带哈希的正式构建，开发及生产一致；素材加载失败保留品牌展示。图片标记“创作示例”，不作为真实客户案例。品牌 Logo 继续引用原始文件，名称取后台配置。

准确生成提示词：`design-prompt.txt`、`light-prompt.txt`、`dark-prompt.txt`。设计图、商品素材来自本聊天内置 imagegen 返回结果；工具未返回可核实的模型版本标识，因此不额外声明实际后端模型版本。

本地代码实施验证见 `../../verification/auth-feima-2026-10-30.md`。2026-10-31 按用户要求已部署至既有服务器，IP 入口双主题与资源验证通过；域名仍受备案限制，详情见 `../../verification/auth-deployment-2026-10-31.md`。部署不代表真实认证写入全链路验收。
