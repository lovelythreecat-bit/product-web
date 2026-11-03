const task=await taskSpace(15);
const page=task.page('p1');
const originalTheme=await page.evaluate(()=>document.documentElement.dataset.theme);
const checks=[];
for(const view of [{name:'desktop',width:1440,height:960,mobile:false},{name:'mobile',width:390,height:844,mobile:true}]) {
  await page.cdp('Emulation.setDeviceMetricsOverride',{width:view.width,height:view.height,deviceScaleFactor:1,mobile:view.mobile});
  for(const theme of ['light','dark']) {
    if(await page.evaluate(()=>document.documentElement.dataset.theme)!==theme) await page.click('.theme-toggle');
    for(const route of ['login','register']) {
      await page.click(`.auth-tabs a[href="/${route}"]`);
      await page.waitForSelector(route==='register'?'#auth-confirmation':'#auth-account');
      await page.waitForFunction(()=>{const img=document.querySelector('.showcase-art');return img?.complete&&img.naturalWidth>0});
      const state=await page.evaluate(()=>({url:location.href,width:innerWidth,theme:document.documentElement.dataset.theme,overflow:document.documentElement.scrollWidth>innerWidth,images:[...document.images].map(img=>({src:img.currentSrc,loaded:img.complete&&img.naturalWidth>0})),fields:document.querySelectorAll('.auth-card input').length,brand:document.querySelector('.brand-name').textContent}));
      if(state.overflow||state.images.some(img=>!img.loaded)||state.width!==view.width) throw new Error(JSON.stringify(state));
      checks.push({viewport:view.name,...state});
      await page.screenshot({path:`F:/Work/电商/web/docs/verification/auth-deployment-2026-10-31/${route}-${theme}-${view.name}.png`});
    }
  }
}
if(await page.evaluate(()=>document.documentElement.dataset.theme)!==originalTheme) await page.click('.theme-toggle');
const ready=await page.fetch('/api/v1/health/ready');
console.log({readyStatus:ready.status,checks});
const fs=await import('node:fs/promises');
await fs.writeFile('F:/Work/电商/web/docs/verification/auth-deployment-2026-10-31/browser-checks.json',JSON.stringify({originalTheme,readyStatus:ready.status,checks},null,2));
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:960,deviceScaleFactor:1,mobile:false});
await page.goto('http://feimadianshang.online/login');
console.log({domainFinalUrl:await page.url()});
console.log(await page.snapshot());
