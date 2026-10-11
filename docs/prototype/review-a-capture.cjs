const {chromium}=require('C:/Users/呜啦啦/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'), path=require('path');
(async()=>{
 const out=path.join(__dirname,'screenshots/review-a');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const observations=[];
 try {
 for(const [device,width,height] of [['desktop',1440,1000],['mobile',390,844]]) {
 const page=await browser.newPage({viewport:{width,height}});page.setDefaultTimeout(6000);
 for(const route of ['home','login','register','workspace','works','account','recharge','admin']) {
 await page.goto('file:///'+path.join(__dirname,'index.html').replace(/\\/g,'/')+'#'+route);await page.waitForTimeout(100);
 await page.screenshot({path:path.join(out,`${device}-${route}.jpg`),fullPage:true,type:'jpeg',quality:80});
 observations.push({device,route,...await page.evaluate(()=>({height:document.documentElement.scrollHeight,width:document.documentElement.scrollWidth,viewport:innerWidth,composer:document.querySelector('.composer')?.getBoundingClientRect().toJSON(),feed:document.querySelector('.feed')?.getBoundingClientRect().toJSON(),text:document.querySelector('main').innerText}))});
 if(route==='admin') for(const mod of ['users','credits','agents','specs','usage','site','logs']) {
 await page.locator('[data-action="admin-'+mod+'"]').click();
 await page.screenshot({path:path.join(out,`${device}-admin-${mod}.jpg`),fullPage:true,type:'jpeg',quality:80});
 }
 }
 await page.goto('file:///'+path.join(__dirname,'index.html').replace(/\\/g,'/')+'#workspace');
 await page.locator('[data-action="assist"]').focus();await page.keyboard.press('Enter');
 observations.push({device,action:'assist-keyboard',...await page.evaluate(()=>({active:document.activeElement.outerHTML.slice(0,250),preview:!!document.querySelector('#preview-prompt')}))});
 await page.locator('[data-action="edit-product"]').click();await page.screenshot({path:path.join(out,`${device}-product-edit.jpg`),type:'jpeg',quality:80});
 await page.keyboard.press('Escape');
 await page.locator('[data-action="generate"]').click();await page.screenshot({path:path.join(out,`${device}-generation-confirm.jpg`),type:'jpeg',quality:80});
 await page.keyboard.press('Escape');
 await page.close();
 }
 fs.writeFileSync(path.join(out,'observations.json'),JSON.stringify(observations,null,2));
 console.log(JSON.stringify(observations.filter(x=>x.route==='workspace'||x.action),null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
