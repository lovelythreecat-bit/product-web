/* Regression checks use browser geometry and real keyboard input, never source-text matching. */
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'C:/Users/呜啦啦/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const phase = process.argv[2] || 'fixed';
const prototypeDir = process.env.PROTOTYPE_DIR || __dirname;
const results = [];
async function check(name, run) {
  try { const evidence = await run(); results.push({ name, pass: true, evidence }); }
  catch (e) { results.push({ name, pass: false, error: e.message }); }
}
function expect(value, message) { if (!value) throw new Error(message); }
(async () => {
  const browser = await chromium.launch({headless:true,channel:'chrome'});
  for (const width of [1440, 390, 850, 851]) {
    const page = await browser.newPage({viewport:{width,height:1000}});
    page.setDefaultTimeout(5000);
    const fresh = async route => {await page.goto(pathToFileURL(path.join(prototypeDir,'index.html')).href+'#'+route);await page.reload();};
    await fresh('workspace');
    await check(`A-01 ${width}px: 输入与记录采用适用列宽和顺序`, async () => {
      const rects=await page.evaluate(()=>Object.fromEntries(['.workspace','.composer','.feed'].map(s=>{const r=document.querySelector(s).getBoundingClientRect();return [s,{left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width}]})));
      const c=rects['.composer'],f=rects['.feed'],w=rects['.workspace'];
      if(width<=850) expect(c.width>=w.width-2&&f.width>=w.width-2&&f.top>=c.bottom,JSON.stringify(rects));
      else expect(f.right<=c.left&&Math.abs(f.top-c.top)<2,JSON.stringify(rects));
      return rects;
    });
    if (![1440,390].includes(width)) { await page.close(); continue; }
    await check(`A-02 ${width}px: 键盘展开辅助后直接编辑建议`,async()=>{
      await page.locator('[data-action="assist"]').focus(); await page.keyboard.press('Enter');
      expect(await page.locator('#preview-prompt').evaluate(e=>e===document.activeElement),'辅助展开后没有聚焦可编辑建议');
      await page.keyboard.press('Control+End');await page.keyboard.type('键盘校验');
      expect((await page.locator('#preview-prompt').inputValue()).endsWith('键盘校验'),'键盘输入没有进入建议');
      await page.keyboard.press('Tab');expect(await page.locator('[data-action="apply-prompt"]').evaluate(e=>e===document.activeElement),'建议后 Tab 未进入采用');
    });
    await check(`A-02 ${width}px: 会话切换与新建保留操作焦点`,async()=>{
      if(width===390){await page.locator('#mobile-session').focus();await page.locator('#mobile-session').selectOption('C-2');expect(await page.locator('#mobile-session').evaluate(e=>e===document.activeElement),'手机会话切换丢失焦点');}
      else {const s=page.locator('[data-action="session"]').last();const id=await s.getAttribute('data-conversation-id');await s.focus();await page.keyboard.press('Enter');expect(await page.locator(`[data-action="session"][data-conversation-id="${id}"]`).evaluate(e=>e===document.activeElement),'桌面会话切换丢失焦点');}
      await page.locator('[data-action="new-session"]:visible').focus();await page.keyboard.press('Enter');expect(await page.locator('#prompt').evaluate(e=>e===document.activeElement),'新建会话没有进入创作输入');
    });
    await fresh('admin');
    await check(`A-02 ${width}px: 后台模块键盘切换保持当前按钮焦点`,async()=>{
      await page.locator('[data-action="admin-users"]').focus();await page.keyboard.press('Enter');expect(await page.locator('[data-action="admin-users"]').evaluate(e=>e===document.activeElement),'后台模块切换丢失焦点');
      await page.keyboard.press('Tab');expect(await page.locator('[data-action="admin-credits"]').evaluate(e=>e===document.activeElement),'后台模块 Tab 顺序重新从页面顶部开始');
    });
    for(const route of ['account','admin']){
      await fresh(route);
      if(route==='admin')await page.locator('[data-action="admin-users"]').click();
      await check(`A-03 ${width}px ${route}: 仅溢出的表格提供可见提示和键盘滚动`,async()=>{
        const wrap=page.locator('.table-wrap').first();
        const info=await wrap.evaluate(e=>({overflow:e.scrollWidth>e.clientWidth+1,tabindex:e.getAttribute('tabindex'),name:e.getAttribute('aria-label'),hint:e.previousElementSibling?.matches('.table-scroll-hint')?{visible:!e.previousElementSibling.hidden,text:e.previousElementSibling.textContent}:null}));
        expect(!!info.hint?.visible===info.overflow,JSON.stringify(info));
        if(info.overflow){expect(info.tabindex==='0'&&!!info.name,JSON.stringify(info));await wrap.focus();await page.keyboard.press('ArrowRight');await page.waitForFunction(()=>document.activeElement.scrollLeft>0);expect(await wrap.evaluate(e=>e.scrollLeft>0),'方向键没有滚动数据表');}
        return info;
      });
    }
    await fresh('workspace');
    await check(`B-2 ${width}px: 合法长商品名、会话与详情不导致整页溢出`,async()=>{
      await page.locator('[data-action="edit-product"]').click();await page.locator('#product-name').fill('A'.repeat(120));await page.locator('#modal-confirm').click();
      const size=()=>page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
      let s=await size();expect(s.scrollWidth<=s.width+1,JSON.stringify(s));
      await page.locator('[data-action="generate"]').click();s=await size();expect(s.scrollWidth<=s.width+1,JSON.stringify(s));
      await page.locator('#modal-confirm').click();
      s=await size();expect(s.scrollWidth<=s.width+1,JSON.stringify(s));
      await page.locator('[data-action="task-detail"]').last().click();await page.locator('#dialog .settings-disclosure summary').click();
      const detail=await page.locator('.overlay-body').evaluate(e=>({width:e.clientWidth,scrollWidth:e.scrollWidth}));expect(detail.scrollWidth<=detail.width+1,JSON.stringify(detail));await page.keyboard.press('Escape');
      await fresh('account');await page.locator('[data-action="edit-profile"]').click();await page.locator('#profile-nickname').fill('A'.repeat(40));await page.locator('#modal-confirm').click();
      s=await size();expect(s.scrollWidth<=s.width+1,JSON.stringify(s));return s;
    });
    await fresh('workspace');
    await check(`B-4 ${width}px: 失败重试文案真实且冻结释放不变`,async()=>{
      await page.locator('[data-action="generate"]').click();await page.locator('#modal-confirm').click();
      await page.locator('.prototype-demo summary').click();await page.locator('[data-action="demo-failed"]').click();
      const released=await page.evaluate(()=>({account:{...Demo.state.account},task:{status:Demo.state.tasks.at(-1).status,settlement:Demo.state.tasks.at(-1).settlement},count:Demo.state.tasks.length}));
      expect(released.task.status==='failed'&&released.task.settlement==='released'&&released.account.frozen===0,'失败任务没有释放');
      await page.locator('[data-action="edit-task"]').click();
      expect(!(await page.locator('#composer').innerText()).includes('原成果保留'),'失败任务承诺保留不存在的成果');
      await page.locator('[data-action="generate"]').click();const text=await page.locator('#dialog').innerText();expect(!text.includes('保留原成果')&&!text.includes('再次收费')&&text.includes('当前报价'),text);
      await page.locator('#modal-confirm').click();const after=await page.evaluate(()=>({account:{...Demo.state.account},count:Demo.state.tasks.length}));
      expect(after.count===released.count+1&&after.account.available===released.account.available-8&&after.account.frozen===8&&after.account.consumed===released.account.consumed,'失败后重试未创建新任务或冻结改变');return {released,after};
    });
    await fresh('workspace');
    await check(`B-4 ${width}px: 有成果的重新生成明示保留与新费用`,async()=>{
      await page.locator('[data-action="task-regenerate"]').first().click();await page.locator('[data-action="generate"]').click();const text=await page.locator('#dialog').innerText();expect(text.includes('保留原成果')&&text.includes('再次收费'),text);await page.keyboard.press('Escape');
    });
    await fresh('works');
    await check(`B-4 ${width}px: 已删除成果的来源不承诺保留成果`,async()=>{
      await page.locator('.action-menu summary').first().click();await page.locator('[data-action="delete-work"]').first().click();await page.locator('#modal-confirm').click();
      await page.locator('header nav a[href="#workspace"]').click();await page.locator('#composer').waitFor();
      await page.locator('[data-action="task-regenerate"][data-task-id="T-1041"]').click();await page.locator('[data-action="generate"]').click();const text=await page.locator('#dialog').innerText();expect(!text.includes('保留原成果')&&text.includes('当前报价'),text);await page.keyboard.press('Escape');
    });
    await page.close();
  }
  await browser.close();
  const report={phase,passed:results.filter(r=>r.pass).length,failed:results.filter(r=>!r.pass).length,results};
  fs.writeFileSync(path.join(__dirname,`review-fix-check-${phase}.json`),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));process.exitCode=report.failed?1:0;
})().catch(e=>{console.error(e);process.exitCode=1;});
