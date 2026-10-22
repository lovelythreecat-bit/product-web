# 我的作品下载菜单验证

2026-10-21。按用户确认，将多图卡片的下载入口合并为一个按钮。悬停显示逐张下载及下载全部，触屏点击展开；单文件保留直接下载。仅修改 ResultViewer 的 galleryLayout 分支及引入 Element Plus Dropdown 样式。

## 已验证

- ego 浏览器真实本地作品页：三图菜单顺序为第一张、第二张、第三张、全部；可移入菜单选择、移出收起。
- 桌面三图卡片展开前后均为 513px，操作区 53px，与相邻单图卡片一致。
- “下载第二张”实际取得文件，服务端文件名为 `taobao-detail_page-feature.png`。批量下载通过单测核对每个文件恰好触发一次，浏览器多文件落盘未做完整验收。
- 390px 触屏模拟：真实触摸事件可打开四项菜单，无横向溢出。
- `works-gallery.spec.ts` 8 项及 `result-preview-navigation.spec.ts` 2 项通过。新增回归测试在修改前因卡片存在三个下载链接而失败，修改后通过；核对单文件选取和全部下载的 URL、顺序、建议文件名。
- `vue-tsc --noEmit`、`vite build` 通过；构建仍有大于 500kB 的分包提示。

## 其他检查发现

扩大检查到 `user-pages-remediation.spec.ts` 时，12 项中 2 项失败：

- `renders real projected work and conversation names and keeps deletion available for video`：该测试使用 `ResultViewer: true` 占位，未渲染现有 actions 插槽，故找不到删除按钮。
- `work filters preserve API kinds and source details avoid raw JSON; deletion remains policy-gated`：仍预期旧 cursor 请求，当前作品页已使用 page / limit / q 参数。

上述两项与本次下载菜单改动无关，未修改其测试或扩大修改页面流程。本轮三文件合计 20 项通过、2 项失败；不是全套测试通过。

截图：[桌面菜单](screenshots/works-download-menu-2026-10-21-desktop.png)、[触屏菜单](screenshots/works-download-menu-2026-10-21-mobile.png)。本次为本地实现和验证，不代表生产发布。
