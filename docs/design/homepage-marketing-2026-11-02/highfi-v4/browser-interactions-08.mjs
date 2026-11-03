const task=await taskSpace(15);const page=task.page('p1');const fs=await import('node:fs/promises');
const base='F:/Work/电商/web/docs/design/homepage-marketing-2026-11-02/highfi-v4/';
await page.evaluate(()=>{document.documentElement.dataset.theme='dark';scrollTo(0,document.querySelector('#guide').offsetTop);dispatchEvent(new Event('exhibitionchange'));});
await page.waitForFunction(()=>Math.abs(window.exhibitionDiagnostics.progress-3)<.01);
await page.click('button[data-mode="pro"]');
const pro=await page.evaluate(()=>({mode:window.exhibitionDiagnostics.mode,visible:!document.querySelector('#pro').hidden,beginnerHidden:document.querySelector('#beginner').hidden}));
await page.screenshot({path:base+'screenshots/pro-dark.png'});
await page.click('button[data-mode="beginner"]');
await page.click('#motion');
const pausedBefore=await page.evaluate(()=>window.exhibitionDiagnostics);
await page.screenshot();
const pausedAfter=await page.evaluate(()=>window.exhibitionDiagnostics);
await page.click('#motion');
await page.click('.hero [data-preview]');
const dialog=await page.evaluate(()=>({open:document.querySelector('dialog').open,focus:document.activeElement.getAttribute('class')}));
await page.keyboard.press('Escape');
await page.click('#theme');
const theme=await page.evaluate(()=>({theme:document.documentElement.dataset.theme,label:document.querySelector('#theme').getAttribute('aria-label')}));
await page.cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
const mobile=[];
for(const color of ['dark','light']){
 await page.evaluate(c=>{document.documentElement.dataset.theme=c;dispatchEvent(new Event('exhibitionchange'));},color);
 for(const [i,id] of ['home','pictures','film','guide','distribution','start'].entries()){
  await page.evaluate(id=>scrollTo(0,document.getElementById(id).offsetTop),id);
  await page.waitForFunction(i=>Math.abs(window.exhibitionDiagnostics.progress-i)<.02,i);
  await page.screenshot({path:base+'screenshots/mobile-'+id+'-'+color+'.png'});
  mobile.push(await page.evaluate(id=>{const c=document.querySelector('#'+id+' .copy').getBoundingClientRect(),s=document.querySelector('#scene').getBoundingClientRect();return{id,theme:document.documentElement.dataset.theme,width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,copyBottom:c.bottom,sceneTop:s.top,renderer:document.documentElement.dataset.renderer};},id));
 }
}
await page.cdp('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
await page.evaluate(()=>scrollTo(0,0));
await page.waitForFunction(()=>window.exhibitionDiagnostics.reduced);
const reducedBefore=await page.evaluate(()=>window.exhibitionDiagnostics);
await page.screenshot();
const reducedAfter=await page.evaluate(()=>({diagnostics:window.exhibitionDiagnostics,disabled:document.querySelector('#motion').disabled}));
await page.cdp('Emulation.setEmulatedMedia',{features:[]});
const result={pro,pauseStable:pausedBefore.time===pausedAfter.time,pausedBefore,pausedAfter,dialog,theme,mobile,reducedBefore,reducedAfter};
await fs.writeFile(base+'interaction-checks.json',JSON.stringify(result,null,2));console.log(result);
