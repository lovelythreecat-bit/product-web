# 独立首页模块

当前维护入口为 **[feima-home-v4](feima-home-v4/README.md)**，可直接打开 [index.html](feima-home-v4/index.html)。此目录是原生 HTML / CSS / JavaScript 独立站，不属于 Vue 构建。

| 位置 | 状态 |
| --- | --- |
| `feima-home-v4/` | 当前采用源码；已按 2026-11-04 记录独立发布到 805 端口 |
| [archive/feima-home-v3/](archive/feima-home-v3/README.md) | 旧独立预览，已被 V4 替代，完整保留供对照 |
| [archive/packages/](archive/packages) | 五个阶段交付 ZIP，只作历史快照，不作为当前源码 |

业务系统首页仍在 `frontend/src/features/site/HomeView.vue`，V4 的业务按钮跳转原业务站点。设计来源、两套首页关系和其他提案见[统一台账](../docs/workspace-map.md)。

后续修改直接落在 V4 源目录；如需交付包，再按交付日期生成，并记录所含版本，不以旧 ZIP 推断最新代码。
