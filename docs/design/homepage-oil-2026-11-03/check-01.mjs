const task=await taskSpace(35);const p=task.page('p1');
await p.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await p.goto('file:///F:/Work/电商/web/docs/design/homepage-oil-2026-11-03/index.html?theme=light');
await p.waitForFunction(()=>[...document.images].filter(i=>i.loading!=='lazy').every(i=>i.complete&&i.naturalWidth>0));
console.log(await p.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,images:[...document.images].map(i=>({src:i.src.split('/').pop(),loaded:i.complete&&i.naturalWidth>0})),gsap:!!window.gsap})));
await p.screenshot({path:'F:/Work/电商/web/docs/design/homepage-oil-2026-11-03/shots/desktop-light.png'});
help('page.screenshot');
console.log(await p.snapshot());
