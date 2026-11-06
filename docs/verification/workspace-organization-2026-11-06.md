# 工作区与首页版本整理 · 2026-11-06

用户确认本次为整理任务：梳理首页多轮改版、独立模块和采用状态，整理归档并保留现有功能及引用。开始时 Git 工作区无未提交修改。

## 当前结论

- 独立首页当前源码：[standalone/feima-home-v4](../../standalone/feima-home-v4/README.md)，设计依据为蓝色图文 V3；有 2026-11-04 的 [805 发布记录](standalone-homepage-805-deployment-2026-11-04.md)。
- 业务系统首页仍为 [HomeView.vue](../../frontend/src/features/site/HomeView.vue)，路由 `/` 使用光场布局＋摄影 V3；有 [11-03 摄影版发布记录](homepage-photo-v3-deployment-2026-11-03.md)。
- 两套首页并存；独立站发布没有替换 Vue 首页。旧稿中“未部署”“待确认”按后续实施和发布证据补充状态，历史正文保留。
- 缺少最终确认记录的设计稿标为“未采用（待确认）”；没有把未确认推定为用户否决。

## 文件归档

所有移动的来源与目标都先核对在当前工作区内，目标原先不存在。共迁移 27 个文件（含一个原本被 Git 忽略的本地 ZIP）。

| 原位置 | 新位置 | 说明 |
| --- | --- | --- |
| `standalone/feima-home-v3/` | `standalone/archive/feima-home-v3/` | 7 个文件，旧实现被 V4 替代，保留完整可打开目录 |
| `standalone/` 下五个 `feima-home-*.zip` | `standalone/archive/packages/` | 原 ZIP 字节不变，不重新打包；用途和 SHA-256 在[归档说明](../../standalone/archive/README.md) |
| `output/home-copy-cleanup-20261103/` | `output/verification/home-copy-cleanup-20261103/` | 6 个历史截图 / 脚本 |
| `output/home-header-20261103/` | `output/verification/home-header-20261103/` | 5 个历史截图 / 脚本 |
| `output/support-header-20261103/` | `output/verification/support-header-20261103/` | 3 个历史截图 / 脚本 |
| `output/figma-assets-20261102.zip` | `output/archive/figma-assets-20261102.zip` | 本地导出包，移动后仍被 Git 忽略 |

新增[工作区与首页版本台账](../workspace-map.md)、[设计导航](../design/README.md)、[独立模块导航](../../standalone/README.md)和[输出导航](../../output/README.md)。22 个首页版本入口新增状态标注；根 README、AGENTS、产品设计入口和 DESIGN 增加当前关系说明。README 的 10-30 首页截图明确标为历史展示。

设计目录之间有相对素材引用，保留原路径；生产源码与素材、原始设计图片、ZIP、历史脚本内容均未改动。V3 归档目录只补充 README；当前 V4 也只补充 README。output 历史脚本保留原会话信息及写入路径，并在目录说明中标明不作为可直接重跑的入口。

本地数据、依赖、缓存、代理状态、临时发布暂存和被其他记录引用的证据没有批量删除。未修改后端、数据库、业务路由、前端构建配置或线上站点。

## 检查结果

- 对整理前建立的 1,001 个文件 SHA-256 清单逐一核对新位置：982 个内容完全相同；其余 19 个是已预期的 Markdown 状态说明修改。无文件缺失，无意外源码、素材或压缩包变化。
- 新增 Markdown 本地目标链接检查通过；迁移后的 V3 与当前 V4 的 HTML / CSS 本地资源引用检查通过。
- `node --check` 检查 V3、V4 的 script.js 均通过；`git diff --check` 通过。
- `git check-ignore output/archive/figma-assets-20261102.zip` 确认归档后的本地导出包仍被忽略。
- 本次仅目录迁移和文档标注，页面代码与运行素材未变；未运行全量业务测试、重新截图或部署，不声称本次完成线上实时核验。

本地核对清单、验证脚本及结果保存在被 Git 忽略的 `tmp/workspace-organize-20261106/`。历史截图与发布记录仍代表各自日期的结果。
