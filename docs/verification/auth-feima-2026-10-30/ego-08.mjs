const task=await taskSpace(14);
const page=task.page('p1');
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1000,height:800,deviceScaleFactor:1,mobile:false});
const tablet=await page.evaluate(()=>({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,form:document.querySelector('.auth-card').getBoundingClientRect().width}));
await page.focus('#auth-account');
await page.keyboard.press('Tab');
const focus=await page.evaluate(()=>document.activeElement.id);
if(focus!=='auth-password') throw new Error('Broken field focus order');
// Deliberate image-error event exercises the production component fallback, without changing app files.
await page.evaluate(()=>document.querySelector('.showcase-art').dispatchEvent(new Event('error')));
await page.waitForSelector('.showcase-brand');
const fallback=await page.evaluate(()=>({visible:!!document.querySelector('.showcase-brand'),hasForm:!!document.querySelector('#auth-confirmation'),brokenImage:!!document.querySelector('.showcase-art')}));
await page.screenshot({path:'F:/Work/电商/web/docs/verification/auth-feima-2026-10-30/artwork-fallback.png'});
console.log({tablet,focus,fallback});
const fs=await import('node:fs/promises');
await fs.writeFile('F:/Work/电商/web/docs/verification/auth-feima-2026-10-30/additional-checks.json',JSON.stringify({tablet,focus,fallback},null,2));
await task.finish({keep:[]});
