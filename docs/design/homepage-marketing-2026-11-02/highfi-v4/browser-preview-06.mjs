const task=await taskSpace(15);const page=task.page('p1');
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';scrollTo(0,0);});
console.log({hero:await page.screenshot()});
console.log(await page.snapshot());
await page.mouse.move(1000,470,{label:'move camera through product scene'});
await page.mouse.wheel(0,1000,{label:'unfold product images in space'});
console.log({images:await page.screenshot()});
console.log(await page.evaluate(()=>window.exhibitionDiagnostics));
