const task=await taskSpace(11),page=task.page('p1'),mobile=task.page('p2');
const base='file:///F:/Work/%E7%94%B5%E5%95%86/web/docs/design/homepage-marketing-2026-11-02/lowfi-v1/index.html';
const dir='F:/Work/电商/web/docs/design/homepage-marketing-2026-11-02/lowfi-v1/screenshots';
await page.goto(base);
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
const ids=await page.evaluate(()=>[...document.querySelectorAll('.module')].map(n=>n.id));
const results=[];
for(const id of ids){
  await page.goto(base+'?module='+id+'&shot=1');
  await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await page.evaluate(async()=>{await Promise.all([...document.images].map(i=>{i.loading='eager';return i.decode().catch(()=>{});}));});
  results.push(await page.evaluate(()=>({module:new URLSearchParams(location.search).get('module'),width:innerWidth,height:document.querySelector('.selected .module').offsetHeight,overflow:document.documentElement.scrollWidth>innerWidth,audit:window.COPY_AUDIT})));
  await page.screenshot({path:dir+'/'+id+'-desktop.png',fullPage:true});
}
await mobile.goto(base+'?module=m01&shot=1');
await mobile.cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await mobile.screenshot({path:dir+'/m01-mobile.png',fullPage:true});
results.push(await mobile.evaluate(()=>({device:'mobile',width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,audit:window.COPY_AUDIT})));
await mobile.goto(base+'?module=m07&shot=1');
await mobile.cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await mobile.evaluate(async()=>{await Promise.all([...document.images].map(i=>{i.loading='eager';return i.decode().catch(()=>{});}));});
await mobile.screenshot({path:dir+'/m07-mobile.png',fullPage:true});
await mobile.goto(base);
await mobile.cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
results.push(await mobile.evaluate(()=>({device:'mobile-all',width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,modules:[...document.querySelectorAll('.module')].map(n=>({id:n.id,right:n.getBoundingClientRect().right})),mismatch:[...document.querySelectorAll('[data-copy]')].filter(n=>n.textContent.replace(/\s/g,'')!==window.SOURCE_BLOCKS.find(b=>b.id===n.dataset.copy).text.replace(/\s/g,'')).map(n=>n.dataset.copy)})));
await page.goto(base);
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
const fs=await import('node:fs/promises');await fs.writeFile('F:/Work/电商/web/docs/design/homepage-marketing-2026-11-02/lowfi-v1/browser-checks.json',JSON.stringify(results,null,2),'utf8');
console.log({screenshots:ids.length+2,checks:results});
