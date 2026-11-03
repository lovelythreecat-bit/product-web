const task=await taskSpace(14);
const page=task.page('p1');
await page.click('button[aria-label="切换浅色主题"]');
await page.waitForFunction(()=>{const img=document.querySelector('.showcase-art');return img?.complete && img.naturalWidth>0});
await page.screenshot({path:'F:/Work/电商/web/docs/verification/auth-feima-2026-10-30/login-light-desktop-initial.png'});
console.log(await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,scene:document.querySelector('.showcase-scene').getBoundingClientRect().toJSON(),form:document.querySelector('.auth-card').getBoundingClientRect().toJSON()})));
