const task=await taskSpace(14);
const page=task.page('p1');
const stub=() => {
  const originalFetch=window.fetch.bind(window);
  window.__authUiRequests=[];
  window.fetch=async (input,init) => {
    const path=new URL(typeof input==='string'?input:input.url,location.origin).pathname;
    if(path==='/api/v1/me') return new Response('{}',{status:401,headers:{'Content-Type':'application/json'}});
    if(path==='/api/v1/site/brand') return new Response(JSON.stringify({name:'飞马'}),{headers:{'Content-Type':'application/json'}});
    if(path==='/api/v1/auth/login'||path==='/api/v1/auth/register') {
      window.__authUiRequests.push({path,body:JSON.parse(init.body)});
      await new Promise(resolve=>setTimeout(resolve,900));
      return new Response('{}',{status:401,headers:{'Content-Type':'application/json'}});
    }
    return originalFetch(input,init);
  };
};
await page.cdp('Page.addScriptToEvaluateOnNewDocument',{source:`(${stub.toString()})()`});
await page.goto('http://127.0.0.1:15173/login');
await page.waitForSelector('#auth-account');
const checks=[];
for(const viewport of [{name:'desktop',width:1440,height:960,mobile:false},{name:'mobile',width:390,height:844,mobile:true}]) {
  await page.cdp('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:viewport.mobile});
  for(const mode of ['light','dark']) {
    if(await page.evaluate(()=>document.documentElement.dataset.theme)!==mode) await page.click('.theme-toggle');
    for(const route of ['login','register']) {
      await page.click(`.auth-tabs a[href="/${route}"]`);
      await page.waitForSelector(route==='register'?'#auth-confirmation':'#auth-account');
      await page.waitForFunction(()=>{const img=document.querySelector('.showcase-art');return img?.complete && img.naturalWidth>0});
      const metrics=await page.evaluate(()=>({width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth,theme:document.documentElement.dataset.theme,fields:document.querySelectorAll('.auth-card input').length,art:document.querySelector('.showcase-art').currentSrc,showcase:getComputedStyle(document.querySelector('.auth-showcase')).display,shellBottom:document.querySelector('.app-shell--auth').getBoundingClientRect().bottom,capabilitiesBottom:document.querySelector('.showcase-capabilities').getBoundingClientRect().bottom,buttonHeight:document.querySelector('button[type=submit]').getBoundingClientRect().height}));
      if(metrics.width!==viewport.width||metrics.overflow||(viewport.name==='desktop'&&metrics.shellBottom>viewport.height)) throw new Error(JSON.stringify(metrics));
      checks.push({route,viewport:viewport.name,...metrics});
      await page.screenshot({path:`F:/Work/电商/web/docs/verification/auth-feima-2026-10-30/${route}-${mode}-${viewport.name}.png`});
    }
  }
}
const fs=await import('node:fs/promises');
await fs.writeFile('F:/Work/电商/web/docs/verification/auth-feima-2026-10-30/layout-checks.json',JSON.stringify(checks,null,2));
console.log(checks);
console.log(await page.snapshot());
