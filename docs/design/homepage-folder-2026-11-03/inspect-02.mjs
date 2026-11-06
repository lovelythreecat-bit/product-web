const task = await taskSpace(36);
const page = await task.newPage();
await page.goto('http://127.0.0.1:15173');
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
console.log(await page.screenshot({path:'F:/Work/电商/web/docs/design/homepage-folder-2026-11-03/baseline.png'}));
console.log(await page.url());
