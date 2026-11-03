# 首页低保真原型合同

最新用户要求：先做低保真原型图，经评审后再按原型分区做高保真及实现。继续多 Agent 协作，全部原 HTML 文案完整保留，解决上一版文字密集的问题。仅做 docs 内静态设计原型，不改 frontend/backend，不调用生图。

输入：本目录 copy-inventory.md（全文）与 copy-data.json（精确HTML），项目 DESIGN.md、上一级 README.md。原文已按顶层语义拆成 copy ID。

你只写自己分配 fragments/NAME.html 和 fragments/NAME.md，以及自己的运行报告。不要写公共 CSS、index.html、copy-data、其他片段或状态账本。不能递归派发。

## 片段规则

用 `<section class="module" id="m01" data-title="首屏" data-motion="后续动效意图">` 包每个模块。原文通过 `<div data-copy="C00-01"></div>` 插槽引入，别重新手打或更改文案。你的所有 ID 必须恰好使用一次。可调整顺序，不合并删减。不要把全部模块挤成一屏；目标每个模块约 1440×800 到 1440×1100，自然伸高，正文18px，长度充足。每模块一个焦点，正文约24–32汉字/行，段间距明确。只有低保真黑白灰，不用渐变、复杂装饰、拟真科技舞台。

可用公共类：module-head（标题区）、split（1:1双栏）、split-wide（4:6）、stack（竖向间隔）、copy-wide（最大720px文字）、display-copy（大号标题）、lead-copy（主要标语）、muted-copy（原文说明弱层级）、image-slot（图片占位框，内部写占位用途，不能添加虚假营销语）、tall（高占位）、film-slot（视频横幅占位）、character-slot（玲玲图容器）、columns-2、columns-3、editorial-list、slogan-grid（两列三行）、source-note（低保真评审注释，界面可切换隐藏）、cta-row、rule、flowline、wide-band。不允许自己写 style 标签。需额外样式在报告建议，由主 Agent 集成。

图像：产品使用线框占位。AI只用 `../../../../output/figma-assets-20261102/01-character-front.png`，文件相对最终 index.html。这个路径会由主 Agent 核对。玲玲角色白粉长发、飞马发夹、粉蓝夹克、白色内搭、百褶裙和白靴，不能替换真人；低保真用灰阶显示参考本体。不需要人物的模块不用强塞人物。最多两三个模块出现角色。

原文里的章节编号、标签、说明及重复内容都要保留，不能因它像文案手册而省略。低保真评审栏和动效说明不属于原文，标注并可隐藏。

建议 A：m01首屏(C00)、m02品牌(C01)、m03六组Slogan(C02)、m04产品简介(C03)。B：m05图片卖点、m06视频卖点、m07双工作台+玲玲、m08多店分发（合计覆盖C04），m09三场景(C05，可拆m09a/b/c避免拥挤)。C：m10官网Hero+四卡片、m11信任与收尾(覆盖C06)，m12传播物料(C07，可拆成三模块)，m13 CTA与页尾(C08+C09)。可根据密度拆得更多，但不要增加无原文的营销段落。

写报告时包含模块与 copy ID 映射、动效建议、手机布局、检查方式及未决项。全部原文插槽完整分配，不宣称实际业务已可用。报告完成后等主 Agent 验收。
