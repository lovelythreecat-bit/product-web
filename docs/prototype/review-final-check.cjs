// Independent reviewer verification of the five confirmed prototype defects.
// Local fixture interactions only; no production service or account is used.
const fs=require('fs'),path=require('path'),http=require('http');
const {chromium}=require('C:/Users/呜啦啦/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=__dirname,out=path.join(root,'screenshots/review-final');
const results=[],logs=[];
const check=(name,pass,evidence)=>{results.push({name,pass:!!pass,evidence});if(!pass)throw new Error(name)};
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const server=http.createServer((req,res)=>{
  const rel=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=path.resolve(root,'.'+(rel==='/'?'/index.html':rel));
  if(!file.startsWith(root+path.sep)){res.writeHead(403);return res.end();}
  const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.webm':'video/webm'};
  fs.readFile(file,(e,b)=>{res.writeHead(e?404:200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream'});res.end(e?'Not found':b)});
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const url='http://127.0.0.1:'+server.address().port;
 let browser;
 try{
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
  for(const [device,width,height] of [['desktop',1440,1000],['mobile',390,844]]){
   const page=await browser.newPage({viewport:{width,height}});page.setDefaultTimeout(8000);
   page.on('pageerror',e=>logs.push({device,type:'pageerror',text:e.message}));
   page.on('console',e=>{if(['error','warning'].includes(e.type()))logs.push({device,type:e.type(),text:e.text()})});
   const route=async hash=>{await page.goto(url+'/#'+hash);await page.waitForTimeout(80)};
   await route('workspace');
   await page.locator('[data-action="edit-product"]').click();
   await page.evaluate(()=>{document.querySelector('#modal-cancel').click();document.querySelector('[data-action="generate"]').click()});
   await page.waitForTimeout(80);
   check(device+' previous close cannot erase new confirmation',await page.evaluate(()=>document.querySelector('#dialog').open&&!!document.querySelector('#modal-confirm')&&document.querySelector('#dialog-title').textContent==='确认本次生成'));
   await page.locator('#modal-cancel').click();
   await page.waitForTimeout(80);
   // Preserve original assertions; retain diagnostics if its cleanup also fails.
   const originalChecks=fs.readFileSync(path.join(root,'interaction-check.js'),'utf8').replace('finally {await close();','finally {try{await close();}catch(e){results.push({error:"cleanup: "+e.message,pass:false});}');
   const old=await page.evaluate('('+originalChecks+')()');
   check(device+' existing interaction regression',old.failed===0&&old.passed===38,old);
   await route('workspace');
   const geometry=await page.evaluate(()=>{const c=document.querySelector('.composer').getBoundingClientRect(),f=document.querySelector('.feed').getBoundingClientRect(),w=document.querySelector('.workspace').getBoundingClientRect();return {composer:c.toJSON(),feed:f.toJSON(),workspace:w.toJSON(),scroll:document.documentElement.scrollWidth,viewport:innerWidth}});
   check(device+' workspace readable geometry',device==='mobile'?geometry.composer.width>=geometry.workspace.width-2&&geometry.feed.width>=geometry.workspace.width-2&&geometry.feed.top>=geometry.composer.bottom:geometry.composer.left>geometry.feed.left&&Math.abs(geometry.composer.top-geometry.feed.top)<2,geometry);
   await page.screenshot({path:path.join(out,device+'-workspace.jpg'),fullPage:true,type:'jpeg',quality:85});
   await page.locator('[data-action="assist"]').focus();await page.keyboard.press('Enter');
   check(device+' assist keyboard continuity',await page.evaluate(()=>document.activeElement.id==='preview-prompt'));
   await page.locator('[data-action="cancel-prompt"]').click();
   await page.locator('[data-action="edit-product"]').click();await page.locator('#product-name').fill('A'.repeat(120));await page.locator('#modal-confirm').click();
   const long=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:innerWidth,name:document.querySelector('.summary-title').textContent}));
   check(device+' legal long name fits',long.scroll<=long.viewport&&long.name.length===120,long);
   await page.locator('[data-action="generate"]').click();
   check(device+' long name confirmation fits',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.querySelector('#dialog').scrollWidth<=document.querySelector('#dialog').clientWidth));
   await page.keyboard.press('Escape');
   await page.screenshot({path:path.join(out,device+'-long-name.jpg'),fullPage:true,type:'jpeg',quality:85});
   await route('admin');await page.locator('[data-action="admin-users"]').focus();await page.keyboard.press('Enter');
   check(device+' module keyboard continuity',await page.evaluate(()=>document.activeElement.dataset.action==='admin-users'));
   await route('account');
   const table=await page.evaluate(()=>{const x=document.querySelector('.table-wrap');return {overflow:x.scrollWidth>x.clientWidth,tabindex:x.getAttribute('tabindex'),name:x.getAttribute('aria-label')||x.getAttribute('aria-labelledby'),text:document.querySelector('main').innerText}});
   if(device==='mobile'){
    check('mobile overflowing table discoverable',table.overflow&&table.tabindex==='0'&&!!table.name&&/滑动|横向/.test(table.text),table);
    await page.locator('.table-wrap').first().focus();const before=await page.locator('.table-wrap').first().evaluate(x=>x.scrollLeft);await page.keyboard.press('ArrowRight');await page.waitForTimeout(150);const after=await page.locator('.table-wrap').first().evaluate(x=>x.scrollLeft);
    check('mobile table keyboard scroll',after>before,{before,after});
    await page.screenshot({path:path.join(out,'mobile-account.jpg'),fullPage:true,type:'jpeg',quality:85});
   }else check('desktop fitting table has no unnecessary prompt',!table.overflow&&!/左右滑动/.test(table.text),table);
   await route('workspace');
   await page.locator('[data-action="generate"]').click();await page.locator('#modal-confirm').click();
   const failed=await page.evaluate(()=>{const t=Demo.state.tasks.at(-1);Demo.transition(t.id,'failed');render();return {id:t.id,settlement:t.settlement,account:Demo.clone(Demo.state.account)}});
   await page.locator(`[data-task-id="${failed.id}"] [data-action="edit-task"]`).click();await page.locator('[data-action="generate"]').click();
   const retry=await page.locator('#dialog').innerText();
   check(device+' failed retry truthful copy',!retry.includes('再次收费')&&!retry.includes('保留原成果')&&!retry.includes('原成果保留')&&/新任务|本次生成/.test(retry),retry);
   check(device+' failed original releases credits',failed.settlement==='released',failed);
   await page.screenshot({path:path.join(out,device+'-failed-retry.jpg'),type:'jpeg',quality:85});
   await page.locator('#modal-confirm').click();
   const admitted=await page.evaluate(()=>{const t=Demo.state.tasks.at(-1);return {source:t.snapshot.sourceTaskId,status:t.status,settlement:t.settlement,cost:t.snapshot.quote.credits,available:Demo.state.account.available,frozen:Demo.state.account.frozen}});
   check(device+' retry creates new frozen task',admitted.source===failed.id&&admitted.settlement==='frozen'&&admitted.available===failed.account.available-admitted.cost&&admitted.frozen===admitted.cost,admitted);
   await route('workspace');await page.locator('[data-task-id="T-1041"] [data-action="task-regenerate"]').click();await page.locator('[data-action="generate"]').click();
   check(device+' successful regeneration keeps fee warning',(await page.locator('#dialog').innerText()).includes('再次收费'));
   await page.keyboard.press('Escape');
   await page.evaluate(()=>{Demo.state.works=Demo.state.works.filter(w=>w.taskId!=='T-1041');render()});
   await page.locator('[data-action="generate"]').click();
   check(device+' removed result never promised retained',!/保留原成果|原成果保留/.test(await page.locator('#dialog').innerText()));
   await page.close();
  }
  const page=await browser.newPage();
  for(const width of [320,850,851]){
   await page.setViewportSize({width,height:900});await page.goto(url+'/#workspace');
   const g=await page.evaluate(()=>{const c=document.querySelector('.composer').getBoundingClientRect(),f=document.querySelector('.feed').getBoundingClientRect();return {c:c.toJSON(),f:f.toJSON(),scroll:document.documentElement.scrollWidth,viewport:innerWidth}});
   check('breakpoint '+width,width<=850?g.c.width>width-70&&g.f.width>width-70&&g.f.top>=g.c.bottom:g.c.left>g.f.left,g);
  }
  await page.close();check('browser errors and warnings',logs.length===0,logs);
 }catch(e){results.push({name:'verification error',pass:false,error:e.stack})}
 finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
 const report={date:'2026-10-11',method:'independent local Edge/Playwright reviewer regression',passed:results.filter(x=>x.pass).length,failed:results.filter(x=>!x.pass).length,results,logs,sourceHashes:Object.fromEntries(['app.js','admin.js','model.js','views.js','style.css','index.html'].map(f=>[f,require('crypto').createHash('sha256').update(fs.readFileSync(path.join(root,f))).digest('hex')]))};
 fs.writeFileSync(path.join(root,'review-final-check-results.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({passed:report.passed,failed:report.failed,failures:results.filter(x=>!x.pass)},null,2));
 if(report.failed)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
