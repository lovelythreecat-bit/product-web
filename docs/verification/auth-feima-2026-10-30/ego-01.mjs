const task = await taskSpace('Feima auth implementation 2026-10-30');
const page = task.page('p1');
await page.cdp('Emulation.setDeviceMetricsOverride', { width:1440, height:960, deviceScaleFactor:1, mobile:false });
await page.goto('http://127.0.0.1:15173/login');
console.log({spaceId:task.spaceId});
console.log(await page.snapshot());
