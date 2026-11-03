const task=await taskSpace(15);const page=task.page('p1');const fs=await import('node:fs/promises');
const base='F:/Work/电商/web/docs/design/homepage-marketing-2026-11-02/highfi-v4/';await fs.mkdir(base+'screenshots',{recursive:true});
await page.reload();await page.waitForFunction(()=>window.exhibitionDiagnostics?.texturesPending===0);
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';scrollTo(0,0);});
await page.waitForFunction(()=>window.exhibitionDiagnostics.progress<.01);
const before=await page.evaluate(()=>window.exhibitionDiagnostics);
await page.mouse.move(700,150,{label:'change model viewing angle'});
await page.mouse.move(1200,700,{label:'observe three dimensional response'});
const after=await page.evaluate(()=>window.exhibitionDiagnostics);
const source=JSON.parse(await fs.readFile(base+'../lowfi-v1/copy-data.json','utf8')).map(x=>x.text).join('\n');
const copy=await page.evaluate(source=>{const norm=s=>s.replace(/\s+/g,'');const full=norm(source);return [...document.querySelectorAll('[data-source]')].map(e=>({text:e.textContent,matches:full.includes(norm(e.textContent))}));},source);
const checks={motion:{before,after},copy,views:[]};
for(const theme of ['dark','light']){
 await page.evaluate(theme=>{document.documentElement.dataset.theme=theme;dispatchEvent(new Event('exhibitionchange'));},theme);
 for(const id of ['home','pictures','film','guide','distribution','start']){
  await page.evaluate(id=>scrollTo(0,document.getElementById(id).offsetTop),id);
  const index=['home','pictures','film','guide','distribution','start'].indexOf(id);
  await page.waitForFunction(i=>Math.abs(window.exhibitionDiagnostics.progress-i)<.025,index);
  await page.screenshot({path:base+'screenshots/'+id+'-'+theme+'.png'});
  checks.views.push(await page.evaluate(()=>({theme:document.documentElement.dataset.theme,width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,scene:window.exhibitionDiagnostics.scene,renderer:document.documentElement.dataset.renderer})));
 }
}
await fs.writeFile(base+'checks.json',JSON.stringify(checks,null,2));
console.log({motionChanged:before.time!==after.time,cameraChanged:JSON.stringify(before.camera)!==JSON.stringify(after.camera),copyCount:copy.length,copyDifferences:copy.filter(x=>!x.matches),views:checks.views});
