const task=await taskSpace(11);
const page=task.page('p1');
const dir='F:/Work/电商/web/docs/design/feima-home-2026-10-30/';
for(const theme of ['light','dark']){
 await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await page.goto('file:///'+dir+'index.html?theme='+theme);
 await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0));
 console.log(await page.evaluate(()=>({theme:document.documentElement.dataset.theme||'light',width:innerWidth,height:document.documentElement.scrollHeight,overflow:document.documentElement.scrollWidth>innerWidth})));
 await page.screenshot({path:dir+'home-'+theme+'-hero.png'});
 await page.screenshot({path:dir+'home-'+theme+'-full.png',fullPage:true});
 await page.cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await page.screenshot({path:dir+'home-'+theme+'-mobile.png',fullPage:true});
 console.log(await page.evaluate(()=>({theme:document.documentElement.dataset.theme||'light',width:innerWidth,height:document.documentElement.scrollHeight,overflow:document.documentElement.scrollWidth>innerWidth})));
}
console.log(await page.snapshot());
