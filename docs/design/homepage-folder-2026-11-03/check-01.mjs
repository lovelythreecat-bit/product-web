const task=await taskSpace(36);
const page=task.page('p1');
await page.goto('file:///F:/Work/电商/web/docs/design/homepage-folder-2026-11-03/index.html');
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await page.waitForFunction(()=>document.querySelector('.folders')&&[...document.querySelectorAll('.hero img')].every(img=>img.complete)&&(!window.gsap||gsap.globalTimeline.time()>.7));
console.log(await page.evaluate(()=>({width:innerWidth,height:innerHeight,scroll:document.documentElement.scrollWidth,hero:document.querySelector('.hero').getBoundingClientRect().bottom,broken:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src)})));
await page.screenshot({path:'F:/Work/电商/web/docs/design/homepage-folder-2026-11-03/shots/desktop-hero.png'});
help('page.screenshot');
console.log(await page.snapshot());
