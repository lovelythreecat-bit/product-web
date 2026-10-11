// Evaluate this function in the prototype's browser page. No production APIs.
async () => {
  const results=[],pause=()=>new Promise(r=>setTimeout(r,40));
  const check=(name,ok)=>{results.push({name,pass:!!ok});if(!ok)throw new Error(name)};
  const click=async selector=>{const el=document.querySelector(selector);if(!el)throw new Error('Missing '+selector);el.focus();el.click();await pause();};
  const route=async hash=>{location.hash=hash;render();await pause();};
  const close=async()=>{if(document.querySelector('#dialog').open)await click('#dialog [data-overlay-close]');};
  const input=(id,value)=>{const el=document.querySelector(id);el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));};
  const beforeAdmin=Demo.clone(AdminDemo.state),originalHash=location.hash;
  try {
    await close();Demo.reset('normal');await route('workspace');
    check('默认工作台仅显示商品摘要',document.querySelectorAll('#app [data-product-field]').length===0);
    check('生成设置默认收起',!document.querySelector('.settings-disclosure').open);
    await click('[data-action="edit-product"]');
    check('编辑商品资料打开统一抽屉',document.querySelector('#dialog').matches('.drawer[open]')&&document.querySelectorAll('#dialog [data-product-field]').length===14);
    input('#product-name','取消测试');await click('#modal-cancel');
    check('取消商品编辑保留原资料',draft().productDetails.name==='青瓷马克杯');
    check('取消后焦点回到编辑按钮',document.activeElement.dataset.action==='edit-product');
    await click('[data-action="edit-product"]');input('#product-name','回归商品');await click('#modal-confirm');
    check('保存商品资料更新摘要',draft().productDetails.name==='回归商品'&&document.querySelector('.summary-title').textContent==='回归商品');
    check('编辑不改变历史任务快照',Demo.task('T-1041').snapshot.productDetails.name==='青瓷马克杯');
    const originalPrompt=draft().prompt;await click('[data-action="assist"]');
    check('点击辅助才出现可编辑建议',!!document.querySelector('#preview-prompt')&&Demo.state.tasks.length===3);
    input('#preview-prompt','测试建议');await click('[data-action="apply-prompt"]');
    check('采用建议写入指令且不创建任务',draft().prompt==='测试建议'&&Demo.state.tasks.length===3);
    await click('[data-action="undo-prompt"]');check('撤回建议恢复原指令',draft().prompt===originalPrompt);
    await click('[data-action="generate"]');
    check('生成先打开收费确认且默认焦点在取消',document.querySelector('#dialog').open&&!document.querySelector('#dialog').classList.contains('drawer')&&document.activeElement.id==='modal-cancel');
    const balance=wallet().available;await click('#modal-cancel');check('取消收费不创建任务不冻结积分',wallet().available===balance&&Demo.state.tasks.length===3);
    await click('[data-action="generate"]');await click('#modal-confirm');
    const admitted=Demo.state.tasks.at(-1);check('确认后只创建一个任务并冻结固定费用',Demo.state.tasks.length===4&&wallet().available===balance-8&&admitted.snapshot.productDetails.name==='回归商品');
    Demo.transition(admitted.id,'pending');check('待核查保持冻结且不创建成果',admitted.settlement==='frozen'&&!Demo.state.works.some(w=>w.taskId===admitted.id));
    Demo.transition(admitted.id,'success');const consumed=wallet().consumed;Demo.transition(admitted.id,'success');check('完整成功只消费一次并保留成果',wallet().consumed===consumed&&Demo.state.works.filter(w=>w.taskId===admitted.id).length===1);
    await click('[data-action="task-detail"]');check('任务详情抽屉包含状态与按需展开快照',document.querySelector('#dialog').classList.contains('drawer')&&document.querySelector('#dialog summary').textContent.includes('快照')&&!document.querySelector('#modal-cancel'));await close();
    await click('[data-action="task-preview"]');check('只读预览没有取消或保存按钮',!document.querySelector('#modal-cancel')&&document.querySelector('#modal-confirm').textContent==='关闭');await close();
    await route('works');const workCount=Demo.state.works.length;const more=document.querySelector('.action-menu');check('删除收在更多菜单',!!more&&!more.open);more.open=true;await click('[data-action="delete-work"]');check('删除打开明确危险确认',document.querySelector('#modal-confirm').classList.contains('destructive'));await click('#modal-cancel');check('取消删除保留成果',Demo.state.works.length===workCount);
    await click('[data-action="delete-work"]');await click('#modal-confirm');await route('workspace');
    check('删除作品后保留任务并显示明确提示',Demo.state.works.length===workCount-1&&document.querySelector('[data-task-id="T-1041"]').textContent.includes('作品已移出')&&!document.querySelector('[data-task-id="T-1041"] [data-action="task-preview"]'));
    await route('account');check('个人中心默认展示资料而非编辑表单',!document.querySelector('#profile-nickname')&&!!document.querySelector('[data-action="edit-profile"]'));
    const nickname=Demo.state.profile.nickname;await click('[data-action="edit-profile"]');input('#profile-nickname','取消昵称');await click('#modal-cancel');check('取消个人资料编辑不保存',Demo.state.profile.nickname===nickname);
    await click('[data-action="edit-profile"]');input('#profile-nickname','回归昵称');await click('#modal-confirm');check('保存个人资料更新页面',Demo.state.profile.nickname==='回归昵称'&&document.querySelector('.profile-heading h2').textContent==='回归昵称');
    await click('[data-action="ledger-detail"]');check('流水详情展示变更前后余额',document.querySelector('#dialog-body').textContent.includes('变更前')&&document.querySelector('#dialog-body').textContent.includes('变更后'));await close();
    await route('admin');await click('[data-action="admin-users"]');
    await click('[data-action="manage-user-view"]');check('后台查看用户使用同一只读抽屉',document.querySelectorAll('dialog').length===1&&document.querySelector('#dialog').matches('.drawer[open]'));await click('#dialog [data-action="manage-user-edit"]');
    check('详情内编辑按钮切换到编辑抽屉',document.querySelector('#dialog-title').textContent.includes('编辑用户')&&!!document.querySelector('#modal-cancel'));await close();
    await click('[data-action="manage-user-add"]');check('后台新增使用共享表单且字段无重复ID',document.querySelector('#dialog').classList.contains('drawer')&&new Set([...document.querySelectorAll('[id]')].map(x=>x.id)).size===document.querySelectorAll('[id]').length);await close();
    await click('[data-action="admin-credits"]');check('后台发放与配置表单默认隐藏',!document.querySelector('#manage-grantUser')&&!document.querySelector('#manage-gift'));
    const creditedUser=AdminDemo.state.users[0],creditBefore=creditedUser.available;await click('[data-action="manage-grant-open"]');input('#manage-modal-amount','13');input('#manage-modal-reason','交互回归');await click('#modal-confirm');check('积分发放更新指定后台余额并记录原因',creditedUser.available===creditBefore+13&&AdminDemo.state.ledger[0].reason==='交互回归');
    await click('[data-action="manage-gift-edit"]');input('#manage-modal-gift','250');await click('#modal-confirm');check('赠送配置保存后更新摘要',AdminDemo.state.gift===250);
    await click('[data-action="admin-site"]');check('官网介绍默认只读',!document.querySelector('#manage-intro'));await click('[data-action="manage-site-edit"]');input('#manage-modal-intro','回归介绍');await click('#modal-confirm');check('官网介绍保存后更新预览',AdminDemo.state.intro==='回归介绍'&&document.querySelector('#app').textContent.includes('回归介绍'));
    await click('[data-action="admin-agents"]');await click('[data-action="manage-agent-edit"]');check('Agent配置共用抽屉且凭据不暴露',document.querySelector('#dialog').classList.contains('drawer')&&!document.querySelector('#dialog input[type="password"]'));await close();
    await click('[data-action="admin-specs"]');const spec=AdminDemo.state.specs[0],version=spec.version;await click('[data-action="manage-spec-edit"]');input('#manage-modal-price','9');input('#manage-modal-reason','回归调价');await click('#modal-confirm');check('发布价格更新版本而不修改旧任务',spec.version===version+1&&Demo.task('T-1041').snapshot.quote.credits===8);
    await route('workspace');await click('[data-action="agent-image"]');await click('.settings-disclosure summary');check('不同Agent显示自身参数',!!document.querySelector('[data-parameter="purpose"]')&&!document.querySelector('[data-parameter="duration"]'));
    await click('[data-action="agent-video"]');await click('.settings-disclosure summary');check('视频设置按点击展开',!!document.querySelector('[data-parameter="duration"]'));
    await click('[data-action="new-session"]');await click('[data-action="generate"]');check('缺商品资料时打开编辑抽屉且不受理',document.querySelector('#dialog-title').textContent==='编辑商品资料'&&Demo.state.tasks.length===4);await close();
  } catch(e) {results.push({error:e.message,pass:false});}
  finally {await close();Object.assign(AdminDemo.state,beforeAdmin);Demo.reset('normal');location.hash=originalHash||'#workspace';render();await pause();}
  return {passed:results.filter(x=>x.pass).length,failed:results.filter(x=>!x.pass).length,results};
}
