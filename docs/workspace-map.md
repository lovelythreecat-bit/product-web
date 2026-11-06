# 工作区导航与首页版本台账

核对日期：2026-11-06。依据为本地路由、源码、设计确认记录和既有发布记录；本次未重新访问服务器，不把历史发布记录视为当前线上实时检查。

## 先找当前入口

| 要做什么 | 入口 | 当前状态 |
| --- | --- | --- |
| 修改独立宣传首页 | [独立首页 V4](../standalone/feima-home-v4/README.md) · [打开页面](../standalone/feima-home-v4/index.html) | **已采用、独立发布**；2026-11-04 发布至 805 端口，未替换业务系统首页 |
| 修改业务系统首页 | [HomeView.vue](../frontend/src/features/site/HomeView.vue) · [路由](../frontend/src/router.ts) | **当前业务首页**：光场布局＋摄影 V3，仍挂载 `/`；CSS 与动效在同目录 |
| 找独立首页的采用稿 | [蓝色图文 V3](design/homepage-blue-rich-2026-11-04/revision-v3/README.md) | **已被独立 V4 采用**，并非业务 Vue 首页的替换稿 |
| 找业务首页的采用稿 | [光场创作](design/homepage-bold-2026-11-03/README.md)＋[摄影 V3](design/homepage-photo-v3-2026-11-03/README.md) | **当前采用**；原始稿与最终源码存在后续局部调整，以源码及变更记录为准 |
| 找旧独立首页与交付包 | [独立模块归档](../standalone/archive/README.md) | V3 源码及五个阶段 ZIP 均已归档；最新源文件在 V4 目录 |
| 找其他设计和原型 | [设计导航](design/README.md) · [产品设计记录](product-design.md) | 非首页沿用已确认飞马双主题与对应原型流程 |

独立首页有自己的 V3 / V4 编号；营销稿的 V3 / V4、摄影 V3、早期暖色 V3 是不同系列，不能仅按数字判断新旧或采用情况。

## 工作区目录职责

| 目录 | 用途与整理规则 |
| --- | --- |
| `frontend/`、`backend/` | 业务源码与测试；正式首页由 Vue 路由决定 |
| `standalone/feima-home-v4/` | 当前独立首页源码，保持可独立打开；不重复创建 latest / final 副本 |
| `standalone/archive/` | 被替代的独立版本、不可变阶段交付包与归档说明 |
| `docs/design/` | 设计稿、素材来源、原型及截图；每个首页系列入口注明采用状态；保留现有路径以维持跨稿素材引用 |
| `docs/prototype/` | 非首页流程核对入口；历史首页原型不作为现行首页视觉依据 |
| `docs/verification/` | 按日期保存实施、验收和发布证据，历史记录不覆盖重写 |
| `docs/superpowers/plans/` | 需求实施计划；计划不等于已完成或已采用 |
| `contracts/`、`infra/` | 接口约定、开发环境与运维工具 |
| `assets/readme/` | 仓库展示素材，首页截图为 2026-10-30 历史样式 |
| `output/figma-assets-20261102/` | 玲玲等原始交付素材，仍被设计稿引用，保留路径 |
| `output/verification/` | 从 output 顶层归类的历史浏览器截图与会话脚本 |
| `output/logo-transparent-20261103/` | 透明 Logo 初稿交付；正式引用以 frontend 源码资产为准 |
| `output/archive/` | 本地导出包，不作为当前源文件 |
| `tmp/`、`.tmp/` | 既有临时验证、发布暂存与排障文件，已被 Git 忽略；有历史证据引用，未批量清空 |
| `.agent-runs/`、`.superpowers/`、`.impeccable/` | 本地代理运行或工具状态，已被 Git 忽略 |
| `.local-data/`、`node_modules/`、各级缓存和虚拟环境 | 本地数据、依赖与缓存；不当作历史方案搬动 |

## 首页版本台账

状态含义：**当前采用**有源码或后续实施依据；**曾采用，已替代**保留历史确认；**未采用（待确认）**表示未找到该具体稿的实施确认，并不等于用户否决；**已否决**仅用于明确否决记录。设计被采用不代表其中宣传能力、价格、政策均已生产验收。

| 系列 / 版本 | 状态 | 依据与去向 |
| --- | --- | --- |
| [早期原型](prototype/index.html)与[2026-10-11 高保真](design/high-fidelity-2026-10-11/visual-reference.md)的首页 | 历史首页基线，已替代 | 10-13 起首页独立设计；不影响非首页原型流程的参考地位 |
| [10-13 咖啡 V1](design/homepage-2026-10-13/README.md) | **已否决** | design-brief 明确记录用户否决咖啡主题 |
| 同系列多品类 V2 | 历史中间稿，已被 V3 替代 | V3 同步确认文案，V2 保留版本追溯 |
| 同系列文案同步 V3 | **曾采用，已替代** | 已确认实施；后续飞马蓝色主题与光场布局覆盖 |
| [10-14 暖色动效 V1](design/homepage-motion-2026-10-14/README.md) | **未采用（待确认）**，历史提案 | design-notes.json 记录待评阅、未接入；未找到后续实施确认 |
| [飞马 UI 10-29 / 10-30](design/feima-ui-2026-10-29/README.md) | **共享视觉仍采用；首页构图已替代** | 非首页仍用飞马双主题；当前首页分别见两条源码入口 |
| [飞马宣传重设计 V1 / V2](design/feima-home-2026-10-30/README.md) | **未采用（待确认）** | 原 README 明确两个具体稿都未获实施确认；非上述飞马 UI 确认稿 |
| [营销初始设计 V1](design/homepage-marketing-2026-11-02/design-v1/README.md) | **未采用（待确认）**，历史探索 | 未找到此图获准实施的记录 |
| [营销低保真 V1](design/homepage-marketing-2026-11-02/lowfi-v1/README.md) | **结构曾确认，后被需求纠正覆盖** | 仅授权高保真；“全部原文上屏”要求已在 11-03 被纠正 |
| [营销高保真 V2](design/homepage-marketing-2026-11-02/highfi-v2/README.md) | **未采用**，历史稿 | 高保真未获实施确认，后续 V3 / V4 探索与文案纠正覆盖 |
| [营销高保真 V3](design/homepage-marketing-2026-11-02/highfi-v3/README.md) | **未采用**，历史稿 | 用户指出缺少真正 3D 动效；选择探索方向不等于批准成稿 |
| [空间叙事 V4 / V4.1](design/homepage-marketing-2026-11-02/highfi-v4/README.md) | **未采用（待确认）** | V4 程序化模型被否决后修订 V4.1；没有具体最终稿的实施确认 |
| [动态概念 V2](design/homepage-motion-concept-2026-11-02/README.md) | **曾采用，已替代** | 11-03 确认并接入 Vue，随后光场布局覆盖 |
| [保温杯配图](design/homepage-images-2026-11-03/README.md) | **曾采用，已替代** | 曾接入动态首页；当前 Vue 改用摄影 V3，旧素材仍供历史稿引用 |
| [光场创作 V1](design/homepage-bold-2026-11-03/README.md) | **当前业务首页布局采用** | 已接入 Vue；[发布记录](verification/homepage-lightfield-deployment-2026-11-03.md) |
| [创意配图 V2](design/homepage-art-direction-2026-11-03/README.md) | **整组未采用，输入图被复用** | 后续摄影 V3 取代风格；phone-source 保留作商品输入参考 |
| [摄影配图 V3](design/homepage-photo-v3-2026-11-03/README.md) | **当前业务首页素材采用** | 源码引用 photo-v3；[11-03 发布记录](verification/homepage-photo-v3-deployment-2026-11-03.md) |
| [商品登场 / oil V1](design/homepage-oil-2026-11-03/README.md) | **未采用（待确认）** | 独立网页设计稿，原记录待评审，未找到实施确认 |
| [创作档案 / folder](design/homepage-folder-2026-11-03/README.md) | **未采用（待确认）** | 固定视觉方向的提案，未找到具体稿获准实施记录 |
| [蓝色图文深化 V2](design/homepage-blue-rich-2026-11-04/README.md) | **设计迭代基础，已由 V3 修订稿替代** | 不作为当前独立首页最终对照稿 |
| [蓝色图文定向修订 V3](design/homepage-blue-rich-2026-11-04/revision-v3/README.md) | **当前独立首页采用稿** | [V4 实施记录](design/homepage-blue-rich-2026-11-04/replica-v4/integration-report.md)明确按三张 V3 稿实现，后续已独立发布 |
| [独立 HTML V3](../standalone/archive/feima-home-v3/README.md) | **已实现预览，已被 V4 替代** | 旧实现用于对比，未找到独立发布记录；已归档 |
| [独立 HTML V4](../standalone/feima-home-v4/README.md) | **当前独立首页，已采用并发布** | 含宽屏、动效、业务跳转；[805 发布记录](verification/standalone-homepage-805-deployment-2026-11-04.md) |

## 后续维护

新增版本时记录系列、日期、采用状态、确认/实施/发布证据，以及替代了哪个版本。稿件只有设计完成时写“待确认”；确认、实现与发布分别记录。历史页面可继续保留自身时间点的说明，但入口的最新状态优先。

当前业务首页与独立首页并存是实际结构，不能把独立 V4 发布解读为 Vue 首页已迁移。未找到批准记录的提案先保留，不由整理任务代替用户作设计决策。

本轮迁移和检查见[整理记录](verification/workspace-organization-2026-11-06.md)。
