# 首页部署一致性验收（2026-10-29）

用户要求线上首页包含本地图片，内容与本地一致。本次仅发布现有两张首页创作示例插图，不迁移用户素材、作品或任务历史。

## 修改

- HomeView 开发和生产共用现有 V3 展示内容，保留“创作示例”标识与真实案例接口。
- Vite 插件 `frontend/scripts/homepage-assets.ts` 仅发布两张已批准 PNG，继续禁用整个 public 目录复制，不发布来源元数据。
- 更新首页单测、素材来源说明和产品设计记录。

## 验证

- 首页及用户菜单相关测试：2 个文件，19 项通过。
- `npm run build`（含 vue-tsc）通过；现有大分包体积提示不影响构建。
- 源文件、构建及服务器上的两张图片 SHA256 一致，HTTP 返回 200 image/png。
- 构建插件移出被忽略的 build 目录后重新构建；全部输出文件逐字节与已发布包相同，无需重复发布。
- ego 浏览器比较本地 http://127.0.0.1:15173/ 与线上 http://feimadianshang.online/，桌面 1440×1000、手机 390×844。
- 两种尺寸下整页正文、图片路径/自然尺寸、七个主要区块的宽高均相同；12 处图片加载成功，无横向溢出。
- 比较采用相同深色主题。导航账号区因本地未登录、线上已登录而不同，正文比较不包含该区域。线上主题已恢复检查前的浅色设置。
- 本轮临时开发服务在检查后停止。

## 发布与回滚

- 线上入口：http://feimadianshang.online/ （HTTP 80，未启用 HTTPS）。
- 部署目录：`/opt/yingzuo/releases/20261029/web/frontend/dist`。
- 先复制资源、最后替换 index.html；原版本备份：`/srv/yingzuo/backups/homepage-before-20261029.tar.gz`。
- 回滚时先将备份解压到临时目录，核对资源后复制到 dist，最后原子替换 index.html。

验收数据与截图见 [记录目录](homepage-deployment-parity-2026-10-29/)。手机验收依据 home-browser-07.mjs 当轮输出：两侧 viewport=390×844、clientWidth=390，contentEqual/imagesEqual/layoutEqual 均为 true。七个区块尺寸依次为 390×757、390×72、390×1310、390×1323、390×656、390×477、390×236。之前中断的浏览器轮次延迟覆盖了手机 JSON，因此不将被覆盖的文件归档为本次通过记录。
