from pathlib import Path
from html.parser import HTMLParser
from html import escape
import json

BASE = Path(__file__).resolve().parent
SOURCE = Path('C:/Users/呜啦啦/xwechat_files/wxid_vv50iqeqcari22_b443/msg/file/2026-11/飞马电商工作台-营销文案.html')
class Node:
    def __init__(self, tag, attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []
class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.root=Node('root'); self.stack=[self.root]
    def handle_starttag(self, tag, attrs):
        n=Node(tag,attrs); self.stack[-1].children.append(n)
        if tag not in {'br','meta','link','img','hr','input'}: self.stack.append(n)
    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag,attrs)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag: del self.stack[i:]; break
    def handle_data(self, text): self.stack[-1].children.append(text)
def nodes(node):
    yield node
    for ch in node.children:
        if isinstance(ch,Node): yield from nodes(ch)
def content(node):
    if isinstance(node,str): return node
    return ''.join(content(ch) for ch in node.children)
def html(node):
    if isinstance(node,str): return escape(node)
    if node.tag=='br': return '<br>'
    attrs=' class="source-'+escape(node.attrs.get('class','').replace(' ',' source-'))+'"' if node.attrs.get('class') else ''
    return '<'+node.tag+attrs+'>'+''.join(html(ch) for ch in node.children)+'</'+node.tag+'>'
p=Parser();p.feed(SOURCE.read_text(encoding='utf-8-sig'))
body=next(n for n in nodes(p.root) if n.tag=='body')
wrap=next(n for n in nodes(body) if n.attrs.get('class')=='wrap')
groups=[n for n in wrap.children if isinstance(n,Node)]
blocks=[]
for group_index,group in enumerate(groups):
    children=[n for n in group.children if isinstance(n,Node)]
    if group.attrs.get('class')=='foot': children=[group]
    flattened=[]
    for child in children:
        if child.attrs.get('class') in {'grid2','grid3','cta-list'}:
            flattened.extend(n for n in child.children if isinstance(n,Node))
        else: flattened.append(child)
    for index,node in enumerate(flattened,1):
        blocks.append({'id':f'C{group_index:02d}-{index:02d}','group':f'C{group_index:02d}','tag':node.tag,'text':content(node).strip(),'html':html(node)})
(BASE/'copy-data.json').write_text(json.dumps(blocks,ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'copy-data.js').write_text('window.SOURCE_BLOCKS = '+json.dumps(blocks,ensure_ascii=False)+';\n',encoding='utf-8')
(BASE/'copy-inventory.md').write_text('# 原文区块清单\n\n'+ '\n\n'.join('## '+b['id']+'\n\n'+b['text'] for b in blocks)+'\n',encoding='utf-8')
print(json.dumps({'blocks':len(blocks),'groups':{g:sum(b['group']==g for b in blocks) for g in dict.fromkeys(b['group'] for b in blocks)}},ensure_ascii=False))
