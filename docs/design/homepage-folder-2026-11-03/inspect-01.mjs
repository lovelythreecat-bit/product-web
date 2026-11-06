const task = await taskSpace('飞马首页层叠版式 1103');
const page = task.page('p1');
await page.goto('file:///C:/Users/呜啦啦/xwechat_files/wxid_vv50iqeqcari22_b443/msg/file/2026-11/index.html');
await page.cdp('Emulation.setDeviceMetricsOverride', {width:1440,height:1000,deviceScaleFactor:1,mobile:false});
console.log({space:task.spaceId});
console.log(await page.screenshot({path:'F:/Work/电商/web/docs/design/homepage-folder-2026-11-03/reference.png'}));
