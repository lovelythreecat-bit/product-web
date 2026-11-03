const task=await taskSpace(12),page=task.page('p1');
await page.reload();
const checks=[];
for(const [device,width,height] of [['desktop',1440,1100],['mobile',390,844]]){
 await page.cdp('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:device==='mobile'});
 await page.evaluate(async()=>{await Promise.all([...document.querySelectorAll('#m03 img')].map(i=>{i.loading='eager';return i.decode().catch(()=>{});}));});
 checks.push(await page.evaluate(()=>({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,visuals:document.querySelectorAll('#m03 .slogan-visual').length,audit:window.COPY_AUDIT,mismatch:[...document.querySelectorAll('#m03 [data-copy]')].filter(n=>n.textContent.replace(/\s/g,'')!==window.SOURCE_BLOCKS.find(b=>b.id===n.dataset.copy).text.replace(/\s/g,'')).map(n=>n.dataset.copy),imageValid:[...document.querySelectorAll('#m03 img')].every(i=>i.complete&&i.naturalWidth>0)})));
 await page.screenshot({path:'F:/Work/电商/web/docs/design/homepage-marketing-2026-11-02/lowfi-v1/screenshots/m03-'+device+'-v2.png',fullPage:true});
}
const fs=await import('node:fs/promises');await fs.writeFile('F:/Work/电商/web/docs/design/homepage-marketing-2026-11-02/lowfi-v1/slogan-checks-v2.json',JSON.stringify(checks,null,2),'utf8');
await page.goto('file:///F:/Work/%E7%94%B5%E5%95%86/web/docs/design/homepage-marketing-2026-11-02/lowfi-v1/index.html?module=m03');
await page.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
console.log(checks);
await task.finish({keep:['p1']});
