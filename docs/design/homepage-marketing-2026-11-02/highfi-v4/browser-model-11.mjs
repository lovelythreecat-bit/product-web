const task=await taskSpace('feima-v4-model-refinement-20261103');const page=task.page('p1');console.log({spaceId:task.spaceId});
const base='F:/Work/电商/web/docs/design/homepage-marketing-2026-11-02/highfi-v4/';
await page.goto('http://127.0.0.1:18114/highfi-v4/');
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await page.waitForFunction(()=>window.exhibitionDiagnostics?.model==='Shopify MaterialsVariantsShoe');
await page.evaluate(()=>document.documentElement.style.scrollBehavior='auto');
for(const theme of ['dark','light']){await page.evaluate(t=>{document.documentElement.dataset.theme=t;dispatchEvent(new Event('exhibitionchange'));},theme);await page.screenshot({path:base+'screenshots/model-home-'+theme+'.png'});}
await page.evaluate(()=>{document.documentElement.dataset.theme='dark';scrollTo(0,document.querySelector('#pictures').offsetTop);dispatchEvent(new Event('exhibitionchange'));});
await page.waitForFunction(()=>Math.abs(window.exhibitionDiagnostics.progress-1)<.01);
await page.screenshot({path:base+'screenshots/model-pictures-dark.png'});
await page.cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await page.evaluate(()=>scrollTo(0,0));await page.waitForFunction(()=>window.exhibitionDiagnostics.progress<.01);
await page.screenshot({path:base+'screenshots/model-mobile-dark.png'});
console.log(await page.evaluate(()=>({diagnostics:window.exhibitionDiagnostics,overflow:document.documentElement.scrollWidth>innerWidth})));
