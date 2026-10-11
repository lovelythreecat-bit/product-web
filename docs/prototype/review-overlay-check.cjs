const fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/呜啦啦/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const phase=process.argv[2]||'fixed',results=[];
function expect(ok,message){if(!ok)throw new Error(message);}
(async()=>{
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  for(const width of [1440,390]){
    const page=await browser.newPage({viewport:{width,height:1000}});page.setDefaultTimeout(5000);
    const fresh=async route=>{await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href+'#'+route);await page.reload();};
    const check=async(name,run)=>{try{results.push({name:`R-06 ${width}px ${name}`,pass:true,evidence:await run()});}catch(e){results.push({name:`R-06 ${width}px ${name}`,pass:false,error:e.message});}};
    await fresh('workspace');
    await check('原生 close→立即 open：旧事件不清空新弹窗或提交动作 / 焦点',async()=>{
      const evidence=await page.evaluate(async()=>{
        let submitted='';openOverlay({title:'第一份确认',body:'<p>第一份</p>',submit:()=>{submitted='old'}});
        const el=document.querySelector('#dialog'),closed=new Promise(resolve=>el.addEventListener('close',resolve,{once:true}));
        el.close();openOverlay({title:'第二份确认',body:'<p>第二份</p>',submit:()=>{submitted='new'}});
        await closed;
        const after={open:el.open,title:document.querySelector('#dialog-title')?.textContent,focus:document.activeElement.id};
        document.querySelector('#modal-confirm')?.click();return {after,submitted};
      });
      expect(evidence.after.open&&evidence.after.title==='第二份确认'&&evidence.after.focus==='modal-cancel'&&evidence.submitted==='new',JSON.stringify(evidence));return evidence;
    });
    await fresh('workspace');
    await check('收费取消→立即再确认：取消不受理，新确认只冻结一次',async()=>{
      const evidence=await page.evaluate(async()=>{
        const before={tasks:Demo.state.tasks.length,...Demo.state.account};feeConfirm();
        const el=document.querySelector('#dialog'),closed=new Promise(resolve=>el.addEventListener('close',resolve,{once:true}));
        document.querySelector('#modal-cancel').click();document.querySelector('[data-action="generate"]').click();
        await closed;
        const reopened={open:el.open,confirm:!!document.querySelector('#modal-confirm'),focus:document.activeElement.id,tasks:Demo.state.tasks.length,...Demo.state.account};
        document.querySelector('#modal-confirm')?.click();const accepted={tasks:Demo.state.tasks.length,...Demo.state.account};return {before,reopened,accepted};
      });
      const {before,reopened,accepted}=evidence;
      expect(reopened.open&&reopened.confirm&&reopened.focus==='modal-cancel'&&reopened.tasks===before.tasks&&reopened.available===before.available&&reopened.frozen===before.frozen,JSON.stringify(evidence));
      expect(accepted.tasks===before.tasks+1&&accepted.available===before.available-8&&accepted.frozen===before.frozen+8&&accepted.consumed===before.consumed,JSON.stringify(evidence));return evidence;
    });
    await fresh('workspace');
    await check('两次取消→同轮再开：连续旧 close 均不干扰最终确认',async()=>{
      const evidence=await page.evaluate(async()=>{
        const el=document.querySelector('#dialog');let count=0;
        const closed=new Promise(resolve=>el.addEventListener('close',function onClose(){if(++count===2){el.removeEventListener('close',onClose);resolve();}}));
        feeConfirm();document.querySelector('#modal-cancel').click();feeConfirm();document.querySelector('#modal-cancel').click();feeConfirm();
        await closed;return {open:el.open,confirm:!!document.querySelector('#modal-confirm'),focus:document.activeElement.id,tasks:Demo.state.tasks.length,frozen:Demo.state.account.frozen};
      });
      expect(evidence.open&&evidence.confirm&&evidence.focus==='modal-cancel'&&evidence.tasks===3&&evidence.frozen===0,JSON.stringify(evidence));return evidence;
    });
    await fresh('admin');await page.locator('[data-action="admin-users"]').click();
    await check('已有旧 close 排队时，详情→编辑只切换一次且可保存',async()=>{
      const evidence=await page.evaluate(async()=>{
        const el=document.querySelector('#dialog'),closed=new Promise(resolve=>el.addEventListener('close',resolve,{once:true}));
        openOverlay({title:'先前弹窗',body:'<p>旧内容</p>'});el.close();
        document.querySelector('[data-action="manage-user-view"]').click();
        document.querySelector('#dialog [data-action="manage-user-edit"]').click();
        await closed;
        return {open:el.open,title:document.querySelector('#dialog-title')?.textContent,editable:!!document.querySelector('#manage-modal-nickname')};
      });
      expect(evidence.open&&evidence.title?.includes('编辑用户')&&evidence.editable,JSON.stringify(evidence));
      await page.locator('#manage-modal-nickname').fill('连续弹窗回归');await page.locator('#manage-modal-reason').fill('验证旧关闭事件不能破坏当前编辑');
      const logCount=await page.evaluate(()=>AdminDemo.state.logs.length);await page.locator('#modal-confirm').click();
      const saved=await page.evaluate(()=>({nickname:AdminDemo.state.users[0].nickname,logs:AdminDemo.state.logs.length,open:document.querySelector('#dialog').open}));
      expect(saved.nickname==='连续弹窗回归'&&saved.logs===logCount+1&&!saved.open,JSON.stringify(saved));return {evidence,saved};
    });
    await page.close();
  }
  await browser.close();const report={phase,passed:results.filter(r=>r.pass).length,failed:results.filter(r=>!r.pass).length,results};
  fs.writeFileSync(path.join(__dirname,`review-overlay-check-${phase}.json`),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));process.exitCode=report.failed?1:0;
})().catch(e=>{console.error(e);process.exitCode=1;});
