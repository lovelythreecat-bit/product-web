"""Build a local review gallery; never changes the production application."""
import json, re, html, pathlib, hashlib
from collections import Counter
from PIL import Image
from html.parser import HTMLParser
class Leaves(HTMLParser):
 def __init__(self): super().__init__(); self.parts=[]
 def handle_data(self,data):
  if data.strip(): self.parts.append(data.strip())
base=pathlib.Path(__file__).resolve().parent
low=base.parent/'lowfi-v1'
copy=json.loads((low/'copy-data.json').read_text(encoding='utf-8'))
byid={x['id']:x for x in copy}
modules=[]
for name in ['brand','features','conversion']:
 text=(low/'fragments'/f'{name}.html').read_text(encoding='utf-8')
 for mid,title,body in re.findall(r'<section class="module" id="([^"]+)" data-title="([^"]+)"[^>]*>(.*?)</section>',text,re.S):
  modules.append(dict(id=mid,title=title,copy_ids=re.findall(r'data-copy="([^"]+)"',body)))
entries={}
for folder in ['hero','brand','features','conversion']:
 path=base/folder/'manifest.json'
 if not path.exists(): continue
 data=json.loads(path.read_text(encoding='utf-8-sig'))
 if isinstance(data,dict): data=data.get('modules',data.get('images',data.get('deliverables',[])))
 for row in data:
  row=dict(row); row['folder']=folder
  entries[row.get('module',row.get('id'))]=row
validation=dict(expected_modules=len(modules),modules=[],missing=[],copy_total=len(copy))
nav=[];sections=[];all_ids=[]
for i,m in enumerate(modules):
 mid=m['id'];row=entries.get(mid);all_ids.extend(m['copy_ids'])
 if not row: validation['missing'].append(mid);continue
 im=pathlib.Path(row['image']);im=im if im.is_absolute() else base/row['folder']/im
 if not im.exists(): validation['missing'].append(mid);continue
 rel=im.relative_to(base).as_posix()
 prompt=pathlib.Path(row['prompt']);prompt=prompt if prompt.is_absolute() else base/row['folder']/prompt
 ptext=prompt.read_text(encoding='utf-8-sig')
 norm=lambda s: re.sub(r'\s+','',s)
 prompts_missing=[]
 for cid in m['copy_ids']:
  leaf=Leaves();leaf.feed(byid[cid]['html'])
  absent=[part for part in leaf.parts if norm(part) not in norm(ptext)]
  if absent: prompts_missing.append(dict(id=cid,text=absent))
 with Image.open(im) as pic: size=list(pic.size)
 validation['modules'].append(dict(module=mid,image=rel,dimensions=size,sha256=hashlib.sha256(im.read_bytes()).hexdigest(),copy_ids=m['copy_ids'],prompt_exact_blocks_missing=prompts_missing))
 nav.append(f'<a href="#{mid}"><b>{i+1:02}</b> {html.escape(m["title"])}</a>')
 original=''.join(f'<div class="original-block" data-copy="{cid}">{byid[cid]["html"]}</div>' for cid in m['copy_ids'])
 lowname='m03-desktop-v2.png' if mid=='m03' else f'{mid}-desktop.png'
 notes=row.get('notes','');notes=json.dumps(notes,ensure_ascii=False) if not isinstance(notes,str) else notes
 variant='<details><summary>查看深色首屏对照</summary><a href="hero/m01-dark.png" target="_blank"><img src="hero/m01-dark.png" alt="首屏深色设计图"></a></details>' if mid=='m01' else ''
 sections.append(f'''<section id="{mid}" class="module"><header><div><small>模块 {i+1:02} / 16</small><h2>{html.escape(m['title'])}</h2></div><a class="open" href="{rel}" target="_blank">打开原尺寸 ↗</a></header><a href="{rel}" target="_blank"><img class="design" src="{rel}" alt="{html.escape(m['title'])}高保真图"></a>{variant}<details><summary>对照已确认原型</summary><img src="../lowfi-v1/screenshots/{lowname}" alt="已确认原型"></details><details><summary>完整原文 · {len(m['copy_ids'])} 个区块</summary><div class="original">{original}</div></details><details><summary>提示词与核对备注</summary><p>{html.escape(notes)}</p><a href="{prompt.relative_to(base).as_posix()}" target="_blank">本图完整提示词</a></details></section>''')
counts=Counter(all_ids)
validation['copy_missing']=[cid for cid in byid if counts[cid]==0]
validation['copy_duplicates']=[cid for cid,n in counts.items() if n!=1]
validation['note']='文件/原文映射核对，不是位图OCR或逐字正确性证明；成图差异见QA.md与分组备注。'
(base/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
(base/'module-map.json').write_text(json.dumps(modules,ensure_ascii=False,indent=2),encoding='utf-8')
(base/'all-source-copy.json').write_text(json.dumps(copy,ensure_ascii=False,indent=2),encoding='utf-8')
head='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>飞马首页 · 分模块高保真 V2</title><style>
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;background:#f3f6fb;color:#182843;font:16px/1.7 "Microsoft YaHei UI","PingFang SC",sans-serif}a{color:#1559d6;text-decoration:none}a:focus-visible,summary:focus-visible{outline:3px solid #1559d6;outline-offset:4px}.sidebar{width:244px;position:fixed;inset:0 auto 0 0;overflow:auto;background:white;padding:28px 20px;border-right:1px solid #dbe3ef}.sidebar strong{font-size:23px}.sidebar p{font-size:13px;color:#586b85;margin:6px 0 20px}.sidebar nav a{display:block;padding:8px 4px;color:#586b85;font-size:14px}.sidebar nav b{font-size:11px;color:#1559d6;margin-right:7px}.sidebar a:hover{background:#e9f1ff;color:#1559d6}.sidebar .meta{border-top:1px solid #dbe3ef;margin-top:18px;padding-top:12px}main{margin-left:244px;padding:40px 32px;max-width:1800px}.intro{max-width:1000px;margin:0 0 36px}.intro h1{font-size:32px;margin:0 0 10px}.intro p{color:#586b85;margin:6px 0}.module{background:#fff;border:1px solid #dbe3ef;border-radius:14px;margin-bottom:48px;overflow:hidden;scroll-margin:24px}.module header{display:flex;justify-content:space-between;align-items:center;padding:22px 28px}.module h2{font-size:22px;margin:0}.module small{color:#586b85}.open{font-size:14px}.module img{display:block;width:100%;height:auto}.design{border-top:1px solid #e7edf5}.module details{border-top:1px solid #e7edf5;padding:14px 28px}.module summary{cursor:pointer;color:#586b85}.module details p{white-space:pre-wrap}.original{max-width:900px;margin:24px auto}.original-block{margin:24px 0}.original h1,.original h2{font-size:25px}.original h3{font-size:21px}.source-num{margin-right:10px}.source-tag{font-size:14px;color:#1559d6}.original p{white-space:normal}.source-pill{font-size:20px}@media(max-width:800px){.sidebar{position:static;width:auto;padding:20px}.sidebar nav{display:grid;grid-template-columns:1fr 1fr}.sidebar .meta{display:none}main{margin:0;padding:24px 12px}.intro h1{font-size:26px}.module header{padding:16px;align-items:flex-start;gap:12px}.module h2{font-size:20px}.module details{padding:14px 16px}.open{white-space:nowrap;font-size:12px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
</style><body><aside class="sidebar"><strong>飞马 / 首页设计</strong><p>高保真 V2 · 2026.11.02<br>按已确认原型分区制作</p><nav>'''
tail='''</main></body></html>'''
intro='''</nav><div class="meta"><a href="README.md">设计说明</a><br><a href="QA.md">核对记录</a><br><a href="../lowfi-v1/gallery.html">低保真原型</a></div></aside><main><div class="intro"><h1>逐区看设计，逐区确认。</h1><p>16 张独立高保真图，另附深色首屏对照。点击图片查看原尺寸。</p><p>原型结构已确认；当前为高保真评审稿。展开每图下方可对照原型、完整原文和提示词。动画方案另见设计说明。</p></div>'''
(base/'gallery.html').write_text(head+''.join(nav)+intro+''.join(sections)+tail,encoding='utf-8')
hero=[byid[cid] for cid in ['C00-01','C00-02','C00-03','C00-04']]
(base/'hero/m01-copy.json').write_text(json.dumps(hero,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(found=len(validation['modules']),missing=validation['missing'],copy_missing=validation['copy_missing'],copy_duplicates=validation['copy_duplicates'],prompt_missing={m['module']:m['prompt_exact_blocks_missing'] for m in validation['modules'] if m['prompt_exact_blocks_missing']}),ensure_ascii=False))
