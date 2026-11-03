const task=await taskSpace('feima-v3-exhibition-20261102');
const page=task.page('p1');
const fs=await import('node:fs/promises');
const base='F:/Work/电商/web/docs/design/homepage-marketing-2026-11-02/highfi-v3/';
const url='file:///F:/Work/%E7%94%B5%E5%95%86/web/docs/design/homepage-marketing-2026-11-02/highfi-v3/index.html';
await fs.mkdir(base+'screenshots',{recursive:true});
const source=JSON.parse(await fs.readFile(base+'all-source-copy.json','utf8'));
const results=[];
for(const size of [{name:'desktop',width:1440,height:1000},{name:'mobile',width:390,height:844}]){
 await page.cdp('Emulation.setDeviceMetricsOverride',{width:size.width,height:size.height,deviceScaleFactor:1,mobile:size.name==='mobile'});
 for(const theme of ['dark','light']){
  await page.goto(url+'?theme='+theme);
  await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode().catch(()=>null)));document.documentElement.style.scrollBehavior='auto';});
  const check=await page.evaluate(()=>({theme:document.documentElement.dataset.theme,title:document.title,width:innerWidth,scrollWidth:document.documentElement.scrollWidth,modules:[...document.querySelectorAll('[data-module]')].map(s=>({id:s.id,width:s.getBoundingClientRect().width,height:s.offsetHeight})),copy:[...document.querySelectorAll('[data-copy]')].map(e=>({id:e.dataset.copy,text:e.textContent,visible:e.getBoundingClientRect().height>0&&getComputedStyle(e).visibility!=='hidden',scrollWidth:e.scrollWidth,width:e.clientWidth})),brokenImages:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src),bodyFont:getComputedStyle(document.body).fontSize,motion:document.documentElement.dataset.motion,disabledMotion:document.querySelector('#motion-toggle').disabled}));
  const normalize=s=>s.replace(/\s+/g,'');
  check.differences=source.filter(b=>normalize(b.text)!==normalize(check.copy.find(x=>x.id===b.id)?.text||'')).map(x=>x.id);
  check.count=check.copy.length;check.hiddenCopy=check.copy.filter(x=>!x.visible).map(x=>x.id);check.overflowCopy=check.copy.filter(x=>x.scrollWidth>x.width+1).map(x=>x.id);delete check.copy;
  results.push({viewport:size.name,...check});
  await page.screenshot({path:base+'screenshots/'+size.name+'-'+theme+'.png'});
  if(size.name==='desktop'&&theme==='dark'){
   const bounds=await page.evaluate(()=>[...document.querySelectorAll('[data-module]')].map(s=>{const r=s.getBoundingClientRect();return{id:s.id,x:0,y:r.top+scrollY,width:innerWidth,height:r.height}}));
   await page.evaluate(()=>document.querySelector('.review-controls').style.visibility='hidden');
   for(const b of bounds){const shot=await page.cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:b.x,y:b.y,width:b.width,height:Math.ceil(b.height),scale:1}});await fs.writeFile(base+'screenshots/'+b.id+'.png',Buffer.from(shot.data,'base64'));}
   await page.evaluate(()=>document.querySelector('.review-controls').style.visibility='');
  }
  if(size.name==='mobile'){
   const bounds=await page.evaluate(()=>['m03','m07','m12c','m13'].map(id=>{const r=document.getElementById(id).getBoundingClientRect();return{id,x:0,y:r.top+scrollY,width:innerWidth,height:r.height}}));
   await page.evaluate(()=>document.querySelector('.review-controls').style.visibility='hidden');
   for(const b of bounds){const shot=await page.cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:b.x,y:b.y,width:b.width,height:Math.ceil(b.height),scale:1}});await fs.writeFile(base+'screenshots/'+b.id+'-mobile-'+theme+'.png',Buffer.from(shot.data,'base64'));}
   await page.evaluate(()=>document.querySelector('.review-controls').style.visibility='');
  }
 }
}
await fs.writeFile(base+'browser-checks.json',JSON.stringify(results,null,2));
console.log(results.map(({modules,...r})=>({...r,moduleCount:modules.length})));
