const task = await taskSpace(34);
const page = task.page('p1');
await page.waitForSelector('.hero-title, #hero-title');
await page.cdp('Emulation.setDeviceMetricsOverride', {width:1440,height:1000,deviceScaleFactor:1,mobile:false});
console.log(await page.snapshot());
console.log(await page.screenshot({path:'F:/Work/电商/web/output/home-copy-cleanup-20261103/desktop.png'}));
await page.cdp('Emulation.setDeviceMetricsOverride', {width:390,height:844,deviceScaleFactor:1,mobile:true});
console.log(await page.screenshot({path:'F:/Work/电商/web/output/home-copy-cleanup-20261103/mobile.png'}));
console.log(await page.evaluate(() => ({overflow:document.documentElement.scrollWidth > innerWidth, removed:[...document.querySelectorAll('.explore,.scroll-link,.lingling-link small,.story-steps > p')].length})));
