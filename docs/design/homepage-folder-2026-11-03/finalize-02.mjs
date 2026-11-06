const fs=await import('node:fs/promises');const base='F:/Work/电商/web/docs/design/homepage-folder-2026-11-03';
const task=await taskSpace(36),page=task.page('p1');
await page.goto('http://127.0.0.1:18768/');await page.waitForSelector('.folders');
await page.evaluate(()=>document.querySelectorAll('img').forEach(i=>i.loading='eager'));
await page.waitForFunction(()=>[...document.images].every(i=>i.complete&&i.naturalWidth>0)&&getComputedStyle(document.querySelector('.folders')).opacity==='1');
console.log('Preview ready',await page.url());
console.log('resources',await page.evaluate(()=>({images:document.images.length,broken:[...document.images].filter(i=>!i.naturalWidth).length,missingAnchors:[...document.querySelectorAll('a[href^="#"]')].filter(a=>!document.querySelector(a.getAttribute('href'))).length,themeControls:document.querySelectorAll('[data-theme],.theme,button[aria-label*="主题"]').length})));
for(const [label,width,height]of[['desktop',1440,1000],['mobile',390,844]]){
  await page.cdp('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
  await page.screenshot({path:`${base}/shots/${label}-hero.png`});
  await page.cdp('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
  await page.evaluate(()=>window.scrollTo({top:document.documentElement.scrollHeight,behavior:'instant'}));
  await page.waitForFunction(()=>!gsap.isTweening('.closing h2'));
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
  const fullHeight=await page.evaluate(()=>document.documentElement.scrollHeight);
  const capture=await page.cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:fullHeight,scale:1}});
  await fs.writeFile(`${base}/shots/${label}-full.png`,Buffer.from(capture.data,'base64'));
}
await page.cdp('Emulation.clearDeviceMetricsOverride');
await page.cdp('Emulation.setEmulatedMedia',{features:[]});
await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
await task.finish({keep:['p1']});
