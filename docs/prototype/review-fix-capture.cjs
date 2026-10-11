const fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/呜啦啦/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
  const dir=path.join(__dirname,'screenshots','review-fixed');fs.mkdirSync(dir,{recursive:true});
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  for(const [device,width,height] of [['desktop',1440,1000],['mobile',390,844]]){
    const page=await browser.newPage({viewport:{width,height}});
    const fresh=async route=>{await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href+'#'+route);await page.reload();};
    const capture=async(name,fullPage=false)=>page.screenshot({path:path.join(dir,`${device}-${name}.jpg`),type:'jpeg',quality:85,fullPage});
    await fresh('workspace');await capture('workspace',true);
    await page.locator('[data-action="assist"]').focus();await page.keyboard.press('Enter');await capture('assist-focus',true);
    await fresh('account');await capture('account-table',true);
    await fresh('admin');await page.locator('[data-action="admin-users"]').click();await capture('admin-table',true);
    await fresh('workspace');await page.locator('[data-action="edit-product"]').click();await page.locator('#product-name').fill('A'.repeat(120));await page.locator('#modal-confirm').click();await capture('long-product',true);
    await fresh('workspace');await page.locator('[data-action="generate"]').click();await page.locator('#modal-confirm').click();await page.locator('.prototype-demo summary').click();await page.locator('[data-action="demo-failed"]').click();await page.locator('[data-action="edit-task"]').click();await page.locator('[data-action="generate"]').click();await capture('failed-retry-confirm');
    await page.close();
  }
  await browser.close();console.log('Saved 12 fresh screenshots to screenshots/review-fixed/.');
})().catch(e=>{console.error(e);process.exitCode=1;});
