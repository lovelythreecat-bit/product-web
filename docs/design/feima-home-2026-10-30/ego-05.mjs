const task=await taskSpace(11);
const page=task.page('p1');
await page.cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await page.click('button[aria-label="切换浅色或深色"]');
console.log(await page.evaluate(()=>({theme:document.documentElement.dataset.theme,pressed:document.querySelector('.theme').getAttribute('aria-pressed')})));
await task.finish({keep:[]});
