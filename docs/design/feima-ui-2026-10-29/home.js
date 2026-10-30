const root=document.documentElement;
const toggle=document.getElementById('theme-toggle');
function setTheme(theme){root.dataset.theme=theme;toggle.textContent=theme==='dark'?'浅色外观':'深色外观';toggle.setAttribute('aria-label',theme==='dark'?'切换到浅色主题':'切换到深色主题');document.querySelectorAll('a[href^="workspace.html"]').forEach(a=>a.href=`workspace.html?theme=${theme}`)}
setTheme(new URLSearchParams(location.search).get('theme')==='dark'?'dark':'light');
toggle.addEventListener('click',()=>setTheme(root.dataset.theme==='dark'?'light':'dark'));
const samples={text:['商品文案','把轻盈，穿进日常。','从出门的第一步，到城市的每一段路。清爽的色调，简单的搭配，让日常穿着多一点自在。','从商品资料出发，让卖点更有画面感。'],image:['图片创作','给商品，一个亮眼的画面。','结合商品资料、参考图片与创作要求，探索主图、场景图和海报的不同表达。','图片规格与费用以实际配置为准。'],video:['视频创作','让商品故事，动起来。','以商品介绍和图片为起点，准备视频创作要求，确认方案后开始生成。','此处展示能力说明，不是已生成的视频。']};
const tabs=[...document.querySelectorAll('[role="tab"]')];
function selectTab(tab){tabs.forEach(t=>{t.setAttribute('aria-selected',String(t===tab));t.tabIndex=t===tab?0:-1});document.getElementById('capability-panel').setAttribute('aria-labelledby',tab.id);['sample-kind','sample-title','sample-copy','sample-meta'].forEach((id,i)=>document.getElementById(id).textContent=samples[tab.dataset.kind][i])}
tabs.forEach((tab,i)=>{tab.addEventListener('click',()=>selectTab(tab));tab.addEventListener('keydown',e=>{let next;if(e.key==='ArrowRight'||e.key==='ArrowDown')next=(i+1)%tabs.length;if(e.key==='ArrowLeft'||e.key==='ArrowUp')next=(i+tabs.length-1)%tabs.length;if(e.key==='Home')next=0;if(e.key==='End')next=tabs.length-1;if(next!==undefined){e.preventDefault();selectTab(tabs[next]);tabs[next].focus()}})});
['example-primary','example-secondary'].forEach(id=>document.getElementById(id).addEventListener('click',()=>{document.getElementById('button-feedback').textContent='已点击演示按钮。未提交业务请求。'}));
