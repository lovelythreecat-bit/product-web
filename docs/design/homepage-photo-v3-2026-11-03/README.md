# 首页摄影配图 V3

> 状态核对（2026-11-06）：**当前业务首页素材已采用、已于 2026-11-03 发布。** 依据为 [发布记录](../../verification/homepage-photo-v3-deployment-2026-11-03.md) 及 HomeView.vue 的 photo-v3 引用；下方“未部署”为早期实施阶段状态。 [全部版本台账](../../workspace-map.md)。下文保留原交付时点的记录。


2026-11-03。状态：用户已认可成图质量，并要求由新 agent 接入正式首页。六张新成图与一张输入参考已以 WebP 接入 Vue 首页，本地预览，未部署。

## 入口

- [六张成图与放置位置](overview.html)
- [完整首页效果](index.html)
- [六图与用途总览截图](overview.png)、[浅色首屏](hero-light.png)、[深色首屏](hero-dark.png)、[完整浅色页](full-light.png)
- 已审阅方向：[V3提示词](../homepage-art-direction-2026-11-03/prompts-v3-review.json)
- 实际执行提示词：[手机](digital/prompts.json)、[品类](categories/prompts.json)、[人物](story/prompts.json)

## 本轮决定

用户认为上一版AI味太重，后审阅真实摄影、纸张布景、材质差异、合理光影的提示词。确认图片位置后，三个设计agent分别完成手机静物/细节、三品类、人物分镜。保留已确认的首页布局和飞马蓝色双主题；品牌Logo与玲玲使用原指定素材。

白底图复用原文件，仅出现在“从想法到出片”的第1步，标注“上传的商品原图”。工作台介绍改为两张成图，不再重复白底输入。取消独立生活方式/城市场景图。本次共6张新成图、1张复用输入参考。

| 图片 | 首页用途 |
| --- | --- |
| digital/phone-campaign.png | 首屏主视觉、创作输出、工作台输出 |
| digital/phone-detail.png | 创作输出、工作台输出 |
| categories/beauty-campaign.png | 首屏品类、美妆画廊横图 |
| categories/audio-campaign.png | 首屏品类、耳机画廊横图 |
| categories/shoe-campaign.png | 鞋服画廊大图 |
| story/phone-creator.png | 创作第三步、视频横幅静态分镜 |
| digital/phone-source.png | 仅创作输入，复用旧白底参考 |

## 模型与边界

使用内置 image_gen，保留用户指定 gpt-image-2.5 配置偏好；工具没有型号选择参数或实际型号元数据，不能独立核验型号。旧输入图先查看再用于产品身份参考，新图逐张生成并查看。每组保留完整实际提示词、来源与设计说明。

全部图片为虚构创作示例，人物图不是真实视频，不构成产品实拍证明或客户案例。沿用页面已有营销文案不代表功能上线或业务验收。用户已确认本稿并授权正式首页实施；原 PNG、提示词与独立评审包保留作来源记录。

运行账本：`.agent-runs/homepage-photo-v3-20261103/`。实际验证结果见 [verification.md](verification.md)。

正式接入账本：`.agent-runs/homepage-photo-v3-implementation-20261103/`。见[正式首页验证与截图](../../verification/homepage-photo-v3-implementation-2026-11-03.md)。
