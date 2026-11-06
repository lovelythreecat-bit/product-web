# V3 实际 image_gen 编辑提示词

日期：2026-11-04。方式：内置 `image_gen`，未使用 CLI/API。用户偏好模型标识为 `gpt-image-2.5`；工具无 model 参数，本次沿用现有配置，未独立核验实际后端模型。

所有输出 `transparent_background: false`，保留原完整蓝白画布；透明仅针对 Logo 插入边界。原始 V2 图片未覆盖。

## upper-v3.png

输入：`../previews/upper-v2.png`（编辑目标）、`../../../../frontend/src/assets/feima-logo-transparent.png`（透明官方 Logo 插入源）。

默认输出：`C:/Users/呜啦啦/.codex/generated_images/01a1a58c-3f9a-7320-916a-a2977b70e1fc/exec-cc15d44a-50fd-4209-be91-4b0fce997d26.png`

```text
Use case: text-localization / precise-object-edit.
Edit target: image 1, upper-v2.png, a 1024x1536 Chinese homepage flat design. Image 2 is the transparent official Feima logo, supporting insert only. Produce upper-v3 with the exact same 1024x1536 frame, same blue-white style, all original product photography, identical silver bottle and white-haired Lingling character, cards, module order, body paragraphs and two original CTA buttons preserved. This is a restrained edit of the completed image, not a new design.
Make ONLY these precise changes:
1. Integrate the official transparent logo from image 2 and the exact full brand text “飞马电商工作台” into a compact TOP NAVIGATION at the top of this hero canvas. No white bar, no separate panel, no white rounded square behind logo, no heavy shadow: the navigation must sit directly on the existing blue hero background. The full brand appears once in this hero, in that navigation only. Remove the original duplicate brand from the hero's body. At navigation right put exact links “创作场景 / 行业案例 / 作品展示 / 套餐定价”. Use white text on dark-blue and deep-blue text where background is pale. Allow only small vertical adjustment of hero content to make space; keep main left hero slogan and Lingling visible, right large detail and three switch cards still intact.
2. Right hero preserve the large dual-workbench detail and its three topic switch cards. Exact card names “双工作台”, “玲玲数字人”, “一键多发”. Show “双工作台” clearly selected with blue border and a thin blue progress bar along the selected card's bottom edge. Other two cards stay inactive. Replace ALL existing switch instruction text “点击下方卡片切换 · 也可用键盘 ← → 切换” with exactly “5s轮播或点击切换”. No other explanatory text. This is a static visual mockup of the selected carousel state; do not add literal animation or implementation claims.
3. Replace left aligned “01 品牌定位” with exact centered blue section heading “从想法到出片，快人一步”. Delete “01” entirely. Heading centered across the full module width, with one short thin blue underline centered immediately beneath it. Enough top and bottom whitespace, no number.
4. Keep the three 快 高 神 cards and paragraphs and pictures. Replace only their bold subtitle lines respectively with exact “十分钟高效出片”, “专业级内容表现”, “AI 替你想好”. Delete old “速度感，对应…”, “腾空感，对应…”, “神驹感，对应…” lines completely; do not retain internal discussion words.
5. In the two positioning cards below, remove only the internal prefixes “一句话定位：” and “品牌主张：”. Keep exact remaining heading content: left “电商人的 AI 内容工厂——从想法到出片，只隔一次对话。”; right “让每个电商人，都拥有自己的内容工厂。” Preserve all remaining paragraphs and photo rows.
6. Replace “02 分场景文案” with exact centered blue heading “你的创作方式，由你选择”, same centered short thin blue underline and heading style as section above, no number.
7. Keep all three horizontal scene cards, bodies and images. Replace only their card headings by exact: “小白工作台 · 会说话，就能创作”; “专业工作台 · 创作尽在掌握”; “视频带货 · 让商品动起来”. Remove all internal labels including “首屏引导（用户视角）”, “面向老手”, “抖店主视角”.
Aggressively preserve all unaffected V2 pixels, proportions, illustrations and copy. Do not add more sections. Do not omit any original cards or image rows. Exact Chinese character rendering. Final artifact is an opaque full-page screenshot with original blue-white backgrounds; only the inserted logo has a transparent boundary.
```

## middle-v3.png

输入：`../previews/middle-v2.png`（编辑目标）、`upper-v3.png`（仅标题风格参照）。

默认输出：`C:/Users/呜啦啦/.codex/generated_images/01a1a58c-3f9a-7320-916a-a2977b70e1fc/exec-51584fe4-e54a-430b-a555-969d5c159d05.png`

```text
Use case: text-localization.
Edit target: FIRST reference image middle-v2.png, a complete 1024x1536 middle segment of a Chinese homepage. SECOND image upper-v3.png is ONLY a section-heading style reference (bold centered blue title with short blue underline); do NOT copy any hero, navigation, character, or first-segment layout from it.
Create middle-v3 as a conservative edit of image 1. Keep its exact 1024x1536 framework, blue-white colors, rounded module borders, all product photographs, every text body, all existing cards and their order, industry metrics including 示意 markers, pricing-independent text, and bottom Lingling CTA banner. No new sections. No hero at top.
The ONLY two changes are:
- Replace top left-aligned “03 短视频 / 社群 / 商店文案” with exact title “一套创意，多种营销表达”, horizontally centered over the FULL module width, bold blue text matching image 2's centered heading style, a single short thin blue underline centered directly beneath. Delete “03” completely. Enough top/bottom whitespace; title independent of the content grid. Slightly move the first card down only if needed, but retain ALL three cards, their original photographs and body text: “30 秒短视频口播脚本”, “朋友圈 / 社群文案”, and “应用商店描述”.
- Replace “04 行业案例” with exact centered blue title “让每个行业，都有亮眼作品”, same typography and centered short underline. Delete “04” completely. Keep six original industry cards: 3C 数码配件, 女装, 男装, 食品零食, 饰品配件, 家居日用, all original images, copy and figures “+58%”, “7天→10分钟”, “-31%”, “1→20条/天”, “-90%”, “+42%” and original 示例/示意 boundary note.
Preserve bottom banner with Lingling and exact existing banner copy and CTA. No redesign or random new layout. This must visibly remain the exact same completed V2 screenshot with only the two customer-facing headings substituted and centered; do not rewrite other copy. Render Chinese precisely.
```

## lower-v3.png

输入：`../previews/lower-v2.png`（编辑目标）、`upper-v3.png`（仅标题风格参照）。

默认输出：`C:/Users/呜啦啦/.codex/generated_images/01a1a58c-3f9a-7320-916a-a2977b70e1fc/exec-401352b3-3103-4ab6-8036-026223f6d28b.png`

```text
Use case: text-localization.
Edit target: FIRST reference image lower-v2.png, the 1024x1536 bottom segment of a completed Chinese marketing homepage. SECOND image upper-v3.png is ONLY a heading typography reference: centered bold blue section titles with a short thin blue underline. Do NOT copy the hero/navigation or first-segment content.
Make lower-v3 in the same exact 1024x1536 format. Preserve the original V2 blue-white visual design, pictures, silver bottle, rounded frames, original module/card order, body copy, all prices, all pricing perks, actions, metrics and 示意 markers, footer. It is a restrained image edit, not a new design.
Change ONLY three section headings:
1. Top module: remove “05 功能能力矩阵” and replace with exact “你的电商创作工具箱”, bold blue, horizontally centered across full module width, a short thin blue underline centered beneath. No number. Leave enough breathing room. Retain all original EIGHT capability cards and their pictures/text in the original 4-by-2 grid: 文生图, 文生视频, 风格库, 多尺寸自适应, 批量出片, 智能提示词, 素材库, 一键多店.
2. Middle gallery: remove “06 飞马出片 · 作品墙” and replace with exact centered heading “好商品，值得好好呈现”, same blue type and short centered blue underline. No number. Preserve all three gallery images and labels, tabs “主图 / 详情页 / 海报 / 短视频 / 直播切片 / 种草图 / 包装图 / 活动 Banner” unchanged.
3. Pricing: remove “07 套餐与定价” and replace with exact centered heading “选择适合你的创作方案”, same centered blue style and short underline. No number. Preserve all THREE pricing cards with exact prices “¥0 / 月”, “¥99 / 月”, “¥299 / 月”, same 免费体验版 / 标准版 / 旗舰版 names, existing perks and CTA labels. Preserve metrics “10万+”, “10分钟”, “6大平台”, “95%” and existing 示意 notes.
Allow only small vertical spacing adjustments to heading areas so all original content still fits. Keep the bottom “现在就让飞马替你出片” banner, bottle photos, two CTA buttons, footer logo/text/links and year unchanged. Do not duplicate a hero or navigation. Do not add any internal-field labels. Maintain original card count, images, composition, hierarchy, colors, and information. Exact Chinese text rendering.
```

