# 客服展示页插画来源

- `approved-artwork.png`：用户已确认的 `docs/design/ai-customer-service-2026-11-02/highfi-v1.png` 原样复制。`FairyArtwork.vue` 通过 CSS 仅显示书本、少女、飞马和头像区域，装饰图不替代页面文字。
- `hero.png`：用内置 image_gen 从已确认稿生成无文字首屏场景，保留原角色、服饰、飞马和粉蓝云境。完整提示词在 `hero.prompt.txt`。
- 用户指定偏好模型 `gpt-image-2.5`；内置工具未披露底层型号，不声明型号已核验。
- 原始用户参考：`F:/Work/工作文件夹/电商/客服素材/微信图片_20261102122223_1174_70.png`。
- 两张位图由组件导入，经 Vite 构建作为带哈希的静态资源发布；来源说明和提示词不随网页公开目录发布。
