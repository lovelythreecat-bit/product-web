const task = await taskSpace(11);
const page = task.page('p1');
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await page.goto('file:///F:/Work/电商/web/docs/design/feima-home-2026-10-30/index.html');
await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0));
console.log(await page.evaluate(()=>({title:document.title,width:innerWidth,height:document.documentElement.scrollHeight,overflow:document.documentElement.scrollWidth>innerWidth,images:[...document.images].map(i=>({loaded:i.naturalWidth>0,alt:i.alt}))})));
console.log(await page.screenshot({path:'F:/Work/电商/web/docs/design/feima-home-2026-10-30/home-light-hero.png'}));
console.log(await page.screenshot({path:'F:/Work/电商/web/docs/design/feima-home-2026-10-30/home-light-full.png',fullPage:true}));
