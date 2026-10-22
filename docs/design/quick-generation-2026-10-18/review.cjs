const {chromium}=require('../../../frontend/node_modules/@playwright/test');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true}),reports=[];
 if(process.argv.includes('--board')){const page=await browser.newPage({viewport:{width:1640,height:1400}});await page.goto(require('node:url').pathToFileURL(path.join(__dirname,'review-board.html')).href,{waitUntil:'networkidle'});await page.screenshot({path:path.join(__dirname,'overview.png'),fullPage:true});await browser.close();console.log('Saved overview.png');return;}
 for(const [name,width,height]of[['desktop',1440,1000],['mobile',390,844]]){
  const ctx=await browser.newContext({viewport:{width,height},isMobile:name==='mobile',hasTouch:name==='mobile',reducedMotion:'reduce'}),page=await ctx.newPage(),errors=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));
  async function snap(label){await page.screenshot({path:path.join(__dirname,name+'-'+label+'.png'),fullPage:true});const dims=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,footer:document.querySelector('.wizard:not([hidden]) .wizard-footer')?.getBoundingClientRect().bottom}));assert.ok(dims.scroll<=width,`${name} ${label} overflow`);if(name==='desktop'&&dims.footer)assert.ok(dims.footer<=height,`${label} footer below viewport`);checks.push(label);}
  const click=action=>page.locator(`[data-action="${action}"]`).click();
  await page.goto(require('node:url').pathToFileURL(path.join(__dirname,'index.html')).href+'#entry',{waitUntil:'networkidle'});await snap('01-entry');
  await page.locator('.quick-entry').evaluate(el=>el.click());await page.locator('[data-action="generate-copy"]').waitFor();await snap('02-product');
  await click('edit-product');assert.ok(await page.locator('dialog').evaluate(e=>e.open));await page.keyboard.press('Escape');assert.ok(await page.locator('dialog').evaluate(e=>e.open));
  await page.locator('[name="name"]').fill('不保存的修改');await page.locator('.overlay-actions [data-action="close"]').click();assert.equal(await page.locator('.product-card h3').innerText(),'黑色头戴式耳机');
  await click('edit-product');await snap('02-product-edit');await page.locator('.overlay-actions [data-action="close"]').click();
  assert.equal(await page.locator('.product-card').innerText().then(t=>t.includes('颜色')),false);
  await click('edit-product');
  const contract=await page.evaluate(()=>window.quickGenerationFields);
  for(const [kind]of contract.productKinds){
   await page.locator('#product-form [name="product_type"]').selectOption(kind);
   const expected=contract.productGroups[kind].flatMap(g=>g.fields);
   assert.deepEqual(await page.locator('#product-form [name]').evaluateAll(es=>es.map(e=>e.name)),expected);
   assert.deepEqual(await page.locator('#product-form label').evaluateAll(es=>es.map(e=>e.childNodes[0].textContent.replace(' *',''))),expected.map(k=>contract.productNames[k]));
  }
  await page.locator('.overlay-actions [data-action="close"]').click();checks.push('all-10-product-types-match-existing-fields-and-labels');
  await click('copy-settings');assert.deepEqual(await page.locator('#copy-settings-form [name]').evaluateAll(es=>es.map(e=>e.name)),[...contract.textFields.map(([k])=>k),'instruction']);await page.locator('.overlay-actions [data-action="close"]').click();checks.push('text-6-existing-settings-plus-existing-instruction');
  await click('generate-copy');await snap('02-charge');await click('accept-charge');await page.locator('.copy-editor').waitFor();await snap('03-copy');
  await page.locator('.copy-editor').fill('确认的营销文案：黑色头戴式耳机，日常通勤与休闲场景。');await click('confirm-copy');
  assert.ok(await page.locator('[data-action="generate-images"]').isDisabled());
  await page.locator('#platform').selectOption('taobao');
  for(const v of['main','detail','long'])await page.locator(`[name="output"][value="${v}"]`).check();
  assert.ok(await page.locator('#footer').innerText().then(t=>t.includes('5 张')&&t.includes('60')));
  await snap('04-image-select');await click('generate-images');assert.ok((await page.locator('.charge-list').innerText()).includes('详情图 × 3'));await click('accept-charge');await page.locator('.image-grid').waitFor();
  assert.equal(await page.locator('.result-tile').count(),5);await snap('05-image-results');
  await click('preview-long-0');assert.equal(await page.locator('.long-preview .long-segment').count(),6);await page.locator('.overlay-actions [data-action="close"]').click();
  await click('confirm-images');assert.ok(await page.locator('[data-action="plan-video"]').isDisabled());assert.deepEqual(await page.locator('[name="frame"]').evaluateAll(es=>es.map(e=>e.value)),['reference-1','reference-2']);await page.locator('[name="frame"][value="reference-1"]').check();await snap('06-video');checks.push('video-first-frame-uploaded-materials-only');
  await click('plan-video');await click('accept-charge');await page.locator('[data-action="view-plan"]').waitFor();await snap('07-video-plan');
  await click('view-plan');assert.equal(await page.locator('.overlay-body input,.overlay-body select,.overlay-body textarea').count(),0);const planLabels=await page.locator('.overlay-body dt').allTextContents();assert.ok(planLabels.includes('创意方向')&&planLabels.includes('视频时长')&&planLabels.includes('运镜'));assert.ok(!planLabels.includes('声音')&&!planLabels.includes('节奏要求'));await snap('07-video-plan-details');checks.push('video-plan-existing-readonly-fields');
  await click('render-video');await click('accept-plan');await page.locator('.video-stage').waitFor();await snap('08-complete');
  await page.reload({waitUntil:'networkidle'});assert.ok((await page.locator('.completion-list').innerText()).includes('5 张'));checks.push('local-prototype-draft-restored');
  await page.locator('#demo-error').evaluate(el=>el.click());await page.locator('.error-panel').waitFor();await snap('09-failure');await click('retry-failed');assert.ok((await page.locator('.overlay-body').innerText()).includes('已冻结的 20 积分'));await page.locator('.overlay-actions [data-action="close"]').click();await click('release-failed');await click('accept-release');assert.ok((await page.locator('.error-panel').innerText()).includes('积分已释放'));checks.push('failure-retry-existing-freeze-or-explicit-release');
  assert.equal(errors.length,0);reports.push({viewport:[width,height],name,checks,errors,scope:'Static review prototype only. No real generation or billing.'});await ctx.close();
 }
 await fs.writeFile(path.join(__dirname,'visual-check.json'),JSON.stringify(reports,null,2));await browser.close();console.log(JSON.stringify(reports,null,2));
})().catch(e=>{console.error(e);process.exit(1)});
