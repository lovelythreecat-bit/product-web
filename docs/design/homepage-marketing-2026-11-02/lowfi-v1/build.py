from pathlib import Path
BASE=Path(__file__).resolve().parent
pieces=[(BASE/'fragments'/name).read_text(encoding='utf-8') for name in ['brand.html','features.html','conversion.html']]
prefix='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>飞马首页 · 低保真结构评审</title><link rel="stylesheet" href="wireframe.css"></head><body>
<header class="review-bar"><strong>飞马首页 · 低保真 V1</strong><span id="copy-status">加载原文</span><div class="review-actions"><button id="toggle-notes" aria-pressed="false">隐藏／显示设计注释</button><button id="toggle-overview" aria-pressed="false">紧凑／完整间距</button></div></header>
<aside class="review-intro"><h1>先看结构，再定视觉。</h1><p>这一稿用于确认模块顺序、内容层级、图文比例和留白。全文保留，产品图片用占位，玲玲使用指定素材的灰阶参考；导航和生成按钮只表达位置，不连接业务。模块之间的灰色说明属于评审注释。</p><nav class="module-index" aria-label="原型模块目录"></nav></aside><main>'''
suffix='''</main><footer class="review-footer">评审阶段：低保真结构。待结构确认后按区块生成高保真图，再确认后实施。动画当前仅标注位置与意图，不代表最终效果。</footer><script src="copy-data.js"></script><script src="review.js"></script></body></html>'''
(BASE/'index.html').write_text(prefix+'\n'.join(pieces)+suffix,encoding='utf-8')
print('Built low-fidelity review index.')
