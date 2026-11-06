---
name: Feima UI
description: 已确认的飞马蓝色浅色与深色界面
colors:
  primary: "#1559d6"
  primary-dark: "#79aaff"
  neutral-background: "#f3f6fb"
  neutral-panel: "#ffffff"
  neutral-text: "#182843"
  neutral-muted: "#586b85"
  neutral-border: "#dbe3ef"
  neutral-selected: "#e9f1ff"
  dark-background: "#0b1220"
  dark-panel: "#121e32"
  dark-text: "#eaf1ff"
  dark-muted: "#a4b5ce"
  dark-border: "#2b3d58"
  dark-on-primary: "#091a34"
typography:
  body:
    fontFamily: '"Microsoft YaHei UI", "PingFang SC", "Noto Sans SC", sans-serif'
    fontSize: "16px"
    lineHeight: 1.6
rounded:
  control: "8px"
  panel: "14px"
spacing:
  base: "8px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral-panel}"
    rounded: "{rounded.control}"
    padding: "8px 16px"
  button-primary-dark:
    backgroundColor: "{colors.primary-dark}"
    textColor: "{colors.dark-on-primary}"
    rounded: "{rounded.control}"
---

# Design System: Feima

## Overview

用户于 2026-10-30 确认的飞马蓝色双主题。以清楚的阅读层级、冷白或墨蓝画布、克制的蓝色操作和自然商品摄影组成界面。Logo 按用户 2026-11-03 的替换要求使用透明背景版 `frontend/src/assets/feima-logo-transparent.png`，保留飞马与完整文字，通过 `BrandMark.vue` 与浏览器图标共同引用；品牌名称仍由后台设置。

本文记录共享设计系统；运行时数值由 `frontend/src/styles/tokens.css`、`themes.css` 和 `element-theme.css` 实现，修改时同步维护。

## Colors

浅色使用冷白画布、白色面板、深色文字；深色使用墨蓝画布和蓝灰面板。主要操作、选择态、焦点共享品牌蓝语义。深色主按钮使用深色文字。成功、警告和错误保留独立语义色，不能一律替换成蓝色。

## Typography

中文系统无衬线字体贯穿导航、字段、成果和正文。首页标题强调层级，工作台正文保持易读，长内容完整换行。真实成果文本及其业务含义不因排版修改。

## Layout

首页于 2026-11-03 按用户确认的光场创作稿实施：内容最大宽度（1280px），桌面首屏上方为大标题与说明／行动，下方为全幅商品空间舞台；手机按标题、说明、舞台顺序单列展示。工作台桌面侧栏（230px）、灵活成果区与设置栏（350px，宽屏 380px）；手机沿用可操作的单列流程。快速生成主内容桌面留白（24px）、手机（16px）。保留后台独立内容滚动和表格横向滚动。

## Elevation & Depth

面板主要通过色差与细边框区分，浮层使用共享阴影。自然商品摄影保持原色，不对图片做机械反色。

## Shapes

共享控件使用紧凑圆角，面板使用更柔和圆角。按页面已有功能密度调整，避免给每个字段套装饰卡片。

## Components

按钮、输入、分页和弹层复用现有 Vue / Element Plus 组件。主要导航以底部线条和文字颜色表示当前页面。主题按钮保留浏览器偏好记忆及同源标签同步。首页商品舞台支持方向键、Home / End 和按钮品类选择，鼠标悬停或焦点在舞台内时暂停自动换品；全局暂停、减少动态效果、离屏／后台暂停及路由卸载清理共同控制动效。创作步骤支持桌面滚动或点选，点选后由手动操作接管，手机仅点选。桌面工作台保留既有紧凑按钮例外；触屏主要操作不小于（44px）。

## Do's and Don'ts

- Do：使用语义变量适配两种主题；保留真实字段、只读状态、费用确认和操作流程。
- Do：示例商品图片标记“创作示例”；授权案例继续读取真实接口。
- Don't：将评审说明、色板、控件样例或设计链接放进正式首页。
- Don't：将历史暖色或绿色原型作为新页面的默认视觉。
