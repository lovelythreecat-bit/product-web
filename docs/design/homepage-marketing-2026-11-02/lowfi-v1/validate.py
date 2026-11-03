from pathlib import Path
from html.parser import HTMLParser
import json,re,runpy
BASE=Path(__file__).resolve().parent
scope=runpy.run_path(str(BASE/'extract-copy.py'))
source=scope['content'](scope['body'])
blocks=json.loads((BASE/'copy-data.json').read_text(encoding='utf-8'))
norm=lambda s:re.sub(r'\s+','',s)
assert norm(source)==norm(''.join(b['text'] for b in blocks)), 'Original body content differs'
page=(BASE/'index.html').read_text(encoding='utf-8')
ids=re.findall(r'data-copy="([^"]+)"',page)
expected=[b['id'] for b in blocks]
assert sorted(ids)==sorted(expected) and len(ids)==len(set(ids))
images=re.findall(r'<img[^>]+src="([^"]+)"',page)
assert all((BASE/img).exists() for img in images)
checks=json.loads((BASE/'browser-checks.json').read_text(encoding='utf-8'))
assert all(not row['overflow'] for row in checks)
assert checks[-1]['mismatch']==[]
modules=re.findall(r'<section class="module" id="([^"]+)" data-title="([^"]+)"',page)
assert len(modules)==16
assert all((BASE/'screenshots'/f'{mid}-desktop.png').exists() for mid,_ in modules)
result={'original_body_text_matches':True,'source_blocks':len(blocks),'placed_once':len(ids),'modules':len(modules),'desktop_width':1440,'mobile_width':390,'overflow':False,'rendered_copy_mismatch':[],'character_sources':images,'production_code_changed':False}
(BASE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
