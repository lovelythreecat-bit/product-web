const task = await taskSpace('feima-home-lowfi-20261102');
const page = task.page('p1');
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await page.goto('http://127.0.0.1:18764/docs/design/homepage-marketing-2026-11-02/lowfi-v1/index.html');
console.log({spaceId:task.spaceId});
console.log(await page.evaluate(()=>({audit:window.COPY_AUDIT,modules:[...document.querySelectorAll('.module')].map(n=>({id:n.id,title:n.dataset.title,height:n.offsetHeight})),horizontalOverflow:document.documentElement.scrollWidth>innerWidth,brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src)})));
help('page.screenshot');
