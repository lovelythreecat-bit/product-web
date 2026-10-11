const $ = s => document.querySelector(s);
const app = $('#app');
const {names,prices} = Demo;
let adminTab='tasks',authTab='login',filter='all',modalAction=null,selectedTaskId=null;
const esc = t => String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const go = page => {location.hash=page};
const draft = () => Demo.current().draft;
const wallet = () => Demo.state.account;
const buttons = (items,cls='') => items.map(([label,action])=>`<button class="${cls}" data-action="${action}">${label}</button>`).join('');
const taskButton = (label,action,id) => `<button data-action="${action}" data-task-id="${id}">${label}</button>`;
function toast(text) {
  const el=$('#toast');el.textContent=text;el.style.display='block';
  clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.style.display='none',3500);
}
// One overlay contract for front office and administration.
let overlayOpener=null,overlayOpenerData=null,overlayActive=false,pendingScroll=null;
function finishOverlay() {
  if(!overlayActive)return;
  overlayActive=false;modalAction=null;$('#dialog').innerHTML='';
  const fallback=overlayOpenerData?[...document.querySelectorAll('[data-action]')].find(b=>Object.entries(overlayOpenerData).every(([k,v])=>b.dataset[k]===v)):null;
  (overlayOpener?.isConnected?overlayOpener:fallback)?.focus();
  overlayOpener=null;overlayOpenerData=null;
}
function closeOverlay() {
  $('#dialog').close();
  // Native close events are queued: finish this instance before another can open.
  finishOverlay();
}
function openOverlay({title,body,label='保存',submit=null,drawer=false,danger=false}) {
  const el=$('#dialog');
  if(el.open)return;
  // Also handle a direct native close whose queued event has not arrived yet.
  finishOverlay();overlayActive=true;
  overlayOpener=document.activeElement;
  overlayOpenerData=overlayOpener?.dataset.action?{...overlayOpener.dataset}:null;
  modalAction=submit;
  el.className=drawer?'overlay drawer':'overlay';
  el.innerHTML=`<form id="overlay-form"><div class="overlay-header"><h2 id="dialog-title">${esc(title)}</h2><button type="button" class="plain" data-overlay-close aria-label="关闭${esc(title)}">关闭</button></div><div class="overlay-body" id="dialog-body">${body}<p id="overlay-error" class="form-error" role="alert"></p></div><div class="overlay-footer">${submit?`<button type="button" id="modal-cancel" data-overlay-close>取消</button><button type="submit" class="${danger?'destructive':'primary'}" id="modal-confirm">${esc(label)}</button>`:'<button type="button" id="modal-confirm" data-overlay-close>关闭</button>'}</div></form>`;
  el.querySelectorAll('[data-overlay-close]').forEach(b=>b.onclick=closeOverlay);
  $('#overlay-form').onsubmit=e=>{e.preventDefault();if(!modalAction)return;const error=modalAction(Object.fromEntries(new FormData(e.currentTarget)),e.currentTarget);if(typeof error==='string'){$('#overlay-error').textContent=error;return}if(error===false)return;closeOverlay()};
  el.showModal();
  // Enter never confirms a paid or destructive action on opening.
  (submit?$('#modal-cancel'):$('#modal-confirm')).focus();
}
function dialog(title,body,label,action,options={}) {
  openOverlay({title,body,label,submit:label==='关闭'?null:action,...options});
}
$('#dialog').addEventListener('close',()=>{
  // An old event must not clear the contents, action or focus of a newer overlay.
  if(!$('#dialog').open)finishOverlay();
});
$('#dialog').addEventListener('cancel',e=>{e.preventDefault();closeOverlay()});
function pageHeading(title,desc,extra='') {
  return `<div class="page-heading"><div><h1>${title}</h1><p>${desc}</p></div>${extra}</div>`;
}
function sessionOptions() {
  return Demo.state.conversations.map(c=>`<option value="${c.id}" ${c.id===Demo.state.currentId?'selected':''}>${esc(c.title)} · ${c.id}</option>`).join('');
}
function sidebar() {
  const a=wallet();
  return `<aside class="sidebar"><button class="primary" data-action="new-session">新建会话</button><button class="plain" data-action="works">我的作品</button><h3>最近会话</h3>
    ${Demo.state.conversations.map(c=>`<button class="session plain ${c.id===Demo.state.currentId?'active':''}" data-action="session" data-conversation-id="${c.id}" aria-pressed="${c.id===Demo.state.currentId}">${esc(c.title)}<small>${c.id} · ${c.taskIds.length} 个任务</small></button>`).join('')}
    <div class="balance"><small>可用积分</small><strong>${a.available}</strong><p>冻结 ${a.frozen} · 已消费 ${a.consumed}</p><button class="plain" data-action="recharge">充值积分</button></div></aside>`;
}
function resultOf(t) {return Demo.state.works.find(w=>w.taskId===t.id)?.result}
function sourceNotice(d) {
  const source=Demo.task(d.sourceTaskId);
  if(source?.status==='success'&&source.settlement==='consumed'&&resultOf(source))return {title:'重新生成 · 再次收费',copy:'保留原成果，按当前报价创建新任务并再次收费。'};
  if(source?.status==='failed'&&source.settlement==='released')return {title:'确认重新提交',copy:'原任务失败，积分已释放；沿用原输入，按当前报价创建新任务。'};
  return {title:'确认本次生成',copy:'沿用原输入，按当前报价创建新任务；历史任务与积分记录保留。'};
}
function resultBody(t) {
  const r=resultOf(t);
  if(t.status==='success'&&r) {
    if(r.type==='image') return `<div class="result"><img src="${r.asset}" alt="人工演示样例，非本商品真实AI产出" style="width:100%;max-height:280px;object-fit:contain"></div>`;
    if(r.type==='video') return `<div class="result"><video controls preload="metadata" src="${r.asset}" aria-label="人工演示视频"></video><small>原型短片 / 非真实 AI 产出</small></div>`;
    return `<div class="result"><p class="preserve-lines">${esc(r.text)}</p></div>`;
  }
  if(t.status==='partial') return '<div class="result"><span class="pill warn">临时文案片段 / 不构成作品</span><p>根据已提供商品资料，整理…</p><small>仅临时展示，不可复制为正式作品、入库或扣费。</small></div>';
  const content={success:'作品已移出演示列表，任务与积分记录仍保留。',pending:'正在核查受理状态，积分保持冻结。',saving:'正在等待恢复原结果保存，积分保持冻结。',failed:'任务已确认失败，冻结积分已释放。',running:'任务正在执行，可离开此页面稍后查看。'};
  return `<div class="notice ${t.status==='failed'?'error':t.status==='running'?'':'warn'}">${content[t.status]}</div>`;
}
function taskCard(t) {
  const labels={success:['成功 · 已消费',''],pending:['待核查 · 冻结中','warn'],saving:['保存失败待恢复 · 冻结中','warn'],failed:['失败 · 已释放','error'],running:['执行中 · 冻结中',''],partial:['执行中 · 临时文案片段','warn']};
  const [label,cls]=labels[t.status],s=t.snapshot,q=s.quote;
  const actions=t.status==='success'&&resultOf(t)?taskButton('预览','task-preview',t.id)+taskButton(s.agent==='text'?'复制文案':'下载',s.agent==='text'?'task-copy':'task-download',t.id)+taskButton('重新生成','task-regenerate',t.id):t.status==='success'?taskButton('重新生成','task-regenerate',t.id):t.status==='failed'?taskButton('修改后重新提交','edit-task',t.id):'';
  return `<article class="panel task" data-task-id="${t.id}"><div class="task-top"><div><h3>${names[s.agent]}创作</h3><div class="task-id">任务 ${t.id} · 会话 ${t.conversationId} · 本地演示</div></div><span class="pill ${cls}">${label}</span></div>${resultBody(t)}
    <div class="task-meta"><span>${esc(s.product.split('\n')[0].slice(0,36))}</span><span>本次费用 ${q.credits} 积分 · 演示</span></div><div class="task-actions">${actions}${taskButton('任务详情','task-detail',t.id)}</div></article>`;
}
const parameterOptions={
  text:{length:['文案长度',['通用短文 · 演示能力']],tone:['表达语气',['简洁自然','专业客观']]},
  image:{purpose:['图片用途',['商品主图','场景图','海报']],ratio:['比例 / 尺寸',['1:1 / 1024px · 演示']],style:['画面风格',['简洁棚拍 · 演示']],count:['生成张数',['1 张','多张 · 尚未开放']]},
  video:{duration:['时长',['5 秒 · 演示档位']],ratio:['横竖屏',['竖屏 9:16','横屏 16:9']],resolution:['分辨率',['720p · 演示']],voice:['配音',['无配音']],captions:['字幕',['不添加','添加 · 演示能力']],music:['背景音乐',['无音乐']]}
};
function parameters() {
  const d=draft();
  return `<div class="grid2">${Object.entries(parameterOptions[d.agent]).map(([id,[label,options]])=>`<div class="field"><label for="${id}">${label}</label><select id="${id}" data-parameter="${id}">${options.map(o=>`<option ${o===d.parameters[d.agent][id]?'selected':''} ${o.includes('尚未开放')?'disabled':''}>${o}</option>`).join('')}</select></div>`).join('')}</div>`;
}
function productForm(d) {
  const groups=[['基本信息',['name','category','brand','model']],['常见规格参数',['material','color','size','weight','capacity','package']],['卖点与使用场景',['sellingPoints','audience','scene','notes']]];
  const examples={name:'如：青瓷马克杯',category:'如：家居日用',brand:'填写实际品牌',model:'填写实际型号或货号',material:'如：陶瓷、不锈钢',color:'如：蓝色',size:'如：20 × 15 × 10 cm',weight:'如：300 g',capacity:'如：350 mL / 500 g',package:'如：杯子、杯盖各 1 件',sellingPoints:'填写已有依据的商品特点',audience:'填写实际适用人群',scene:'如：办公室日常饮水',notes:'其他需要在创作中保留的商品事实'};
  return `<div class="product-form"><h3>商品资料</h3><p><small>商品名称必填，其余选填。仅填写真实信息，未知规格留空。</small></p>${groups.map(([title,keys])=>`<fieldset class="product-section"><legend>${title}</legend><div class="grid2">${keys.map(key=>{const label=Demo.productFields.find(([k])=>k===key)[1],isText=['sellingPoints','notes'].includes(key);return `<div class="field ${isText?'field-wide':''}"><label for="product-${key}">${label}${key==='name'?' <span class="required-label">必填</span>':''}</label>${isText?`<textarea id="product-${key}" data-product-field="${key}" maxlength="600" placeholder="${examples[key]}">${esc(d.productDetails[key])}</textarea>`:`<input id="product-${key}" data-product-field="${key}" value="${esc(d.productDetails[key])}" maxlength="120" ${key==='name'?'required':''} placeholder="${examples[key]}">`}</div>`}).join('')}</div></fieldset>`).join('')}</div>`;
}
function editProduct() {
  const d=draft(),editing=Demo.clone(d);
  openOverlay({title:'编辑商品资料',body:productForm(editing),label:'保存商品资料',drawer:true,submit:(_,form)=>{
    const values=Object.fromEntries([...form.querySelectorAll('[data-product-field]')].map(el=>[el.dataset.productField,el.value.trim()]));
    if(!values.name)return '请填写商品名称。';
    d.productDetails=values;d.product=Demo.productText(values);render();toast('商品资料已保存，后续创作使用这些资料。');
  }});
}
function helpDetails(title,body) {return `<details class="context-help"><summary>${title}</summary>${body}</details>`}
function composer() {
  const d=draft(),q=Demo.quote(d);
  return `<section class="panel composer" id="composer"><div class="row spread"><h2>准备本次创作</h2><small>手动选择 Agent</small></div>
    ${d.sourceTaskId?`<div class="notice">来源任务：${esc(d.sourceTaskId)} · 原输入已带回，可编辑。${sourceNotice(d).copy}</div>`:''}
    <div class="agent-tabs" role="group" aria-label="Agent 选择">${Object.keys(names).map(a=>`<button data-action="agent-${a}" class="${a===d.agent?'active':''}" aria-pressed="${a===d.agent}">${names[a]}</button>`).join('')}</div>
    <section class="product-summary"><div class="row spread"><h3>商品资料</h3><button class="plain" data-action="edit-product">${d.productDetails.name?'编辑资料':'填写资料'}</button></div><p class="summary-title">${esc(d.productDetails.name||'还未填写商品名称')}</p><p class="muted summary-copy">${esc([d.productDetails.category,d.productDetails.capacity,d.productDetails.sellingPoints,d.productDetails.scene].filter(Boolean).join(' · ')||'添加商品资料，让创作更贴合商品。')}</p></section>
    <div class="field"><h3>商品图片${d.agent==='text'?'（选填）':'（必填）'}</h3><div class="upload"><input id="material" type="file" accept="image/*" aria-label="选择商品图片" hidden><p id="material-label">${esc(d.material?.available?d.material.name:d.material?'原素材不可用，请重新选择':'尚未选择图片')}</p><button type="button" data-action="choose-material">${d.material?.available?'更换图片':'选择图片'}</button></div></div>
    <div class="field"><label for="prompt">创作指令</label><textarea id="prompt">${esc(d.prompt)}</textarea></div>
    <button class="plain" data-action="assist" aria-expanded="${d.preview!==null}" aria-controls="assist-preview" style="margin-top:8px">AI 帮我完善</button>
    ${d.preview!==null?`<div class="prompt-preview" id="assist-preview"><label for="preview-prompt">辅助建议 · 可编辑</label><textarea id="preview-prompt">${esc(d.preview)}</textarea><p><small>采用后替换创作指令，仍需点击生成才会提交任务。</small></p><div class="row">${buttons([['采用建议','apply-prompt'],['取消','cancel-prompt']])}</div></div>`:''}
    ${d.undo!==null?'<button class="plain" data-action="undo-prompt" style="margin-top:8px">撤回辅助，恢复原指令</button>':''}
    <details class="settings-disclosure"><summary>生成设置 <span id="parameter-summary">${esc(Object.values(d.parameters[d.agent]).join(' / '))}</span></summary>${parameters()}</details>
    <div class="quote"><span>本次费用</span><strong>${q.credits} <small>积分 · 演示值</small></strong></div>
    <p id="composer-error" class="form-error" role="alert"></p><button class="primary generate" data-action="generate" ${wallet().available<q.credits?'disabled':''}>${wallet().available<q.credits?'积分不足，无法生成':'确认费用并生成'}</button>
    ${wallet().available<q.credits?'<button class="plain" data-action="recharge">查看积分说明</button>':''}
    ${helpDetails('费用与原型说明',`<p>受理后冻结，完整保存后消费，确定失败释放。重新生成需再次确认费用。</p><p>规格 ${q.specVersion} / 价格 ${q.priceVersion}。图片仅在本地选择，不上传；辅助不创建任务。生产辅助方案、输入限制和多结果规则待确认。</p>`)}</section>`;
}
function workspace() {
  const c=Demo.current(),active=c.taskIds.includes(selectedTaskId)?selectedTaskId:c.taskIds.at(-1);selectedTaskId=active||null;
  return `<div class="shell">${sidebar()}<div class="work-main">${pageHeading('创作工作台','商品资料、创作指令与任务记录，放在同一个窗口。',`<button data-action="recharge">可用 ${wallet().available} · 充值积分</button>`)}
    <section class="mobile-sessions" aria-label="会话导航"><label for="mobile-session">历史会话</label><div class="row"><select id="mobile-session">${sessionOptions()}</select><button data-action="new-session">新建会话</button></div></section>
    <div class="workspace">${composer()}<section class="feed"><div class="row spread"><h2>${esc(c.title)}</h2><small>会话 ${c.id} · 本地演示</small></div><p class="muted">提交时固定本次输入，后续编辑仅影响新任务。</p>
    ${c.taskIds.map(id=>taskCard(Demo.task(id))).join('')||'<div class="panel empty-state"><h3>还没有任务</h3><p>准备资料并确认费用后，任务将在本会话展示。</p></div>'}
    <details class="prototype-demo"><summary>原型演示区 · 状态与异常切换</summary><p>只改变选定本地任务，不模拟真实服务端事件。终态不逆转，重复操作不结算。</p><label for="demo-task">操作任务</label><select id="demo-task">${c.taskIds.map(id=>`<option value="${id}" ${id===active?'selected':''}>${id} · ${names[Demo.task(id).snapshot.agent]} · ${Demo.task(id).snapshot.quote.credits} 积分</option>`).join('')||'<option>请先生成任务</option>'}</select>
    ${buttons([['完整保存 / 成功','demo-success'],['临时流式片段','demo-partial'],['执行中','demo-running'],['待核查','demo-pending'],['保存失败待恢复','demo-saving'],['确定失败 / 释放','demo-failed'],['空会话','demo-empty'],['报价已失效','demo-quote'],['模拟原素材缺失','demo-material-missing'],['积分不足','demo-insufficient'],['重置演示','demo-reset']])}
    <p>重置/积分不足会原子加载另一完整本地场景，包含会话、任务、作品、账户、流水；不是生产操作。D-01～05、D-08～10 仍待确认。图片/视频为固定人工样例，不能作为新商品效果承诺。</p></details></section></div></div></div>`;
}
function worksPage() {
  const items=Demo.state.works.filter(w=>filter==='all'||w.type===filter);
  return `<div class="page">${pageHeading('我的作品','只展示本人已完整保存的成果。以下均为本地人工演示。',`<button class="primary" data-action="workspace">继续创作</button>`)}<div class="tabs" role="group" aria-label="作品类型筛选">${[['all','全部'],['text','文案'],['image','图片'],['video','视频']].map(([k,v])=>`<button data-action="filter-${k}" class="${filter===k?'active':''}" aria-pressed="${filter===k}">${v}</button>`).join('')}</div>
    <div class="works-grid">${items.map(w=>`<article class="panel" data-work-id="${w.id}"><div class="work-cover ${w.type}">${w.type==='image'?`<img src="${w.result.asset}" alt="人工演示版式样例，非真实AI产出">`:`<span>${w.type==='text'?'商品文案演示':'商品视频演示'}</span>`}<small>人工样例 / 非真实 AI 产出</small></div><span class="pill">${names[w.type]} · 已保存</span><h3 style="margin-top:12px">${esc(w.name)}</h3><p class="muted">${esc(Demo.state.conversations.find(c=>c.id===w.conversationId)?.title)}</p><div class="row wrap">${taskButton('预览','task-preview',w.taskId)+taskButton(w.type==='text'?'复制文案':'下载',w.type==='text'?'task-copy':'task-download',w.taskId)+taskButton('重新生成','task-regenerate',w.taskId)+taskButton('任务详情','task-detail',w.taskId)}<details class="action-menu"><summary>更多</summary><div><button class="danger" data-action="delete-work" data-work-id="${w.id}">删除作品</button></div></details></div></article>`).join('')||'<div class="panel"><h2>暂无该类作品</h2><p>完整成果保存后会出现在这里。</p></div>'}</div>${helpDetails('作品与删除说明','<p>作品均为人工演示。删除仅移出演示列表，保留任务与积分记录；生产生命周期政策待确认。</p>')}</div>`;
}
const profileFields=[['nickname','昵称','text',40],['shopName','店铺名称','text',80],['category','主营类目','text',80],['email','联系邮箱','email',120],['phone','联系电话','tel',40]];
function profileForm(p) {
  return '<p class="muted">联系方式选填，不用于注册或登录验证。</p><div class="grid2">'+profileFields.map(([key,label,type,max])=>'<div class="field"><label for="profile-'+key+'">'+label+(key==='nickname'?' · 必填':'')+'</label><input id="profile-'+key+'" name="'+key+'" type="'+type+'" maxlength="'+max+'" '+(key==='nickname'?'required':'')+' value="'+esc(p[key])+'"></div>').join('')+'</div><div class="field"><label for="profile-bio">个人简介</label><textarea id="profile-bio" name="bio" maxlength="300">'+esc(p.bio)+'</textarea></div>';
}
function editProfile() {
  openOverlay({title:'编辑个人资料',body:profileForm(Demo.state.profile),label:'保存资料',drawer:true,submit:data=>{
    if(!data.nickname.trim())return '请填写昵称。';
    Object.keys(data).forEach(k=>data[k]=data[k].trim());Object.assign(Demo.state.profile,data);render();toast('资料已保存到当前演示账户。');
  }});
}
function ledgerDetail(id) {
  const l=Demo.state.ledger.find(x=>x.id===id);if(!l)return;
  const balances=o=>'<dt>可用 / 冻结 / 已消费</dt><dd>'+o.available+' / '+o.frozen+' / '+o.consumed+'</dd>';
  openOverlay({title:'积分流水详情',drawer:true,body:'<dl class="snapshot"><dt>流水 / 时间</dt><dd>'+esc(l.id)+' / '+esc(l.at)+'</dd><dt>类型 / 数量</dt><dd>'+esc(l.kind)+' / '+l.amount+' 积分</dd><dt>关联任务</dt><dd>'+esc(l.taskId||'无')+'</dd><dt>说明</dt><dd>'+esc(l.note)+'</dd></dl><h3>变更前</h3><dl class="snapshot">'+balances(l.before)+'</dl><h3>变更后</h3><dl class="snapshot">'+balances(l.after)+'</dl>'+(l.taskId?taskButton('查看来源会话','open-task',l.taskId):'')});
}
function account() {
  const a=wallet(),p=Demo.state.profile;
  return '<div class="page">'+pageHeading('个人中心','管理个人资料与积分。')+'<div class="account-grid"><section class="panel profile-panel"><div class="profile-heading"><div class="profile-avatar" aria-hidden="true">'+esc(p.nickname.slice(0,1))+'</div><div><h2>'+esc(p.nickname)+'</h2><p class="muted">'+esc(p.username)+'</p></div><span class="pill">'+esc(p.status)+'</span></div><div class="rule"></div><h3>个人与店铺资料</h3><dl class="profile-meta">'+[['店铺',p.shopName],['主营类目',p.category],['联系邮箱',p.email],['联系电话',p.phone]].map(([label,v])=>'<div><dt>'+label+'</dt><dd>'+esc(v||'未填写')+'</dd></div>').join('')+'</dl><p class="muted">'+esc(p.bio||'还未填写个人简介')+'</p><div class="row wrap"><button class="primary" data-action="edit-profile">编辑资料</button><button data-action="account-detail">账号详情</button></div><div class="rule"></div><button class="plain" data-action="logout">退出登录</button></section><section class="panel"><div class="row spread"><h2>积分账户</h2><button data-action="recharge">充值积分</button></div><div class="balance-grid"><div><small>可用</small><strong>'+a.available+'</strong></div><div><small>冻结</small><strong>'+a.frozen+'</strong></div><div><small>累计消费</small><strong>'+a.consumed+'</strong></div></div><div class="rule"></div><h3>积分流水</h3><div class="table-wrap"><table><thead><tr><th>类型 / 时间</th><th>数量</th><th>关联任务</th><th>操作</th></tr></thead><tbody>'+Demo.state.ledger.map(l=>'<tr data-ledger-id="'+l.id+'"><td>'+esc(l.kind)+'<br><small>'+esc(l.at)+'</small></td><td>'+l.amount+'</td><td>'+(l.taskId?taskButton(l.taskId,'open-task',l.taskId):'注册 / 演示入账')+'</td><td><button data-action="ledger-detail" data-ledger-id="'+l.id+'">查看详情</button></td></tr>').join('')+'</tbody></table></div>'+helpDetails('积分与演示说明','<p>累计入账 '+a.credited+' 积分。赠送与发放不作为支付收入。所有数据仅在本页内存中保存，刷新会重置。</p>')+'</section></div></div>';
}
function recharge() {
  const a=wallet();return `<div class="page"><div class="panel recharge"><h1>充值积分</h1><p class="muted">当前可用积分</p><div class="big">${a.available} <small>冻结 ${a.frozen}</small></div><div class="notice">在线充值暂未开放</div><p style="margin:24px 0">首版使用注册赠送与管理员发放的试用积分。后续计划接入微信、支付宝；兑换比例、档位和退款规则将在支付阶段确认。</p><p class="muted">此页面不会创建订单、调用支付渠道或增加积分。</p><button class="primary" data-action="workspace" style="margin-top:24px">返回创作工作台</button></div></div>`;
}
let tableResizeObserver=null;
function bindScrollableTables() {
  tableResizeObserver?.disconnect();
  tableResizeObserver=new ResizeObserver(entries=>entries.forEach(({target})=>update(target)));
  function update(wrap) {
    const hint=wrap.previousElementSibling,overflow=wrap.scrollWidth>wrap.clientWidth+1;
    hint.hidden=!overflow;
    if(overflow){wrap.tabIndex=0;wrap.setAttribute('aria-describedby',hint.id);}
    else{wrap.removeAttribute('tabindex');wrap.removeAttribute('aria-describedby');}
  }
  app.querySelectorAll('.table-wrap').forEach((wrap,i)=>{
    const hint=document.createElement('p');hint.className='table-scroll-hint';hint.id=`table-scroll-hint-${i}`;
    hint.textContent='左右滑动或使用方向键查看全部列';wrap.before(hint);
    const heading=app.querySelector('h1')?.textContent||'当前页面';
    wrap.setAttribute('role','region');wrap.setAttribute('aria-label',`${heading}数据表：${[...wrap.querySelectorAll('th')].slice(0,2).map(th=>th.textContent).join('、')}`);
    update(wrap);tableResizeObserver.observe(wrap);
  });
}
function render() {
  let route=location.hash.slice(1)||'home';if(route==='register'){authTab='register';route='login'}
  app.innerHTML=({home,workspace,works:worksPage,account,recharge,login:auth,admin}[route]||home)();
  document.querySelectorAll('header nav a').forEach(a=>a.classList.toggle('active',a.hash==='#'+route));
  if($('#composer')) {
    const d=draft();$('#prompt').oninput=e=>{d.prompt=e.target.value};
    if($('#preview-prompt'))$('#preview-prompt').oninput=e=>{d.preview=e.target.value};
    document.querySelectorAll('[data-parameter]').forEach(el=>el.onchange=e=>{d.parameters[d.agent][el.dataset.parameter]=e.target.value;$('#parameter-summary').textContent=Object.values(d.parameters[d.agent]).join(' / ')});
    $('#material').onchange=e=>{const file=e.target.files[0];if(!file)return;d.material={id:`local-${Date.now()}`,version:'v1',name:`${file.name} · 仅本地演示`,available:true};$('#material-label').textContent=d.material.name};
    $('#mobile-session').onchange=e=>{Demo.state.currentId=e.target.value;selectedTaskId=null;render();$('#mobile-session')?.focus()};$('#demo-task').onchange=e=>{selectedTaskId=e.target.value};
  }
  if($('#auth-form'))$('#auth-form').onsubmit=e=>{e.preventDefault();if(authTab==='register'&&$('#password').value!==$('#password-confirm').value){$('#auth-error').textContent='两次密码不一致，请重新确认。';return}toast(authTab==='register'?'演示注册完成，生产赠送积分按确认配置执行。':'已进入演示账户。');go('workspace')};
  if(typeof AdminDemo!=='undefined')AdminDemo.bind();
  bindScrollableTables();
}
function feeConfirm() {
  const d=draft();
  if(d.quoteStale){dialog('报价已更新，尚未受理',`<p>旧报价 ${d.priceVersion} 已失效。未创建任务、未冻结积分。</p><div class="notice">当前演示报价 ${prices[d.agent]} 积分 / demo-p2</div>`,'接受新报价',()=>{d.priceVersion='demo-p2';d.quoteStale=false;render();toast('已展示新报价；请再次确认费用后提交。')});return}
  const error=Demo.validate(d);if(error){$('#composer-error').textContent=error;if(!d.productDetails.name.trim())editProduct();else $('#material')?.focus();return}
  const submitted=Demo.clone(d),conversationId=Demo.state.currentId,q=Demo.quote(submitted),key=`submit-${Date.now()}-${Math.random()}`;
  const source=d.sourceTaskId?sourceNotice(d):null;
  dialog(source?.title||'确认本次生成',`<p class="summary-title">${esc(d.productDetails.name)} · ${names[d.agent]}</p><div class="quote"><span>本次将冻结</span><strong>${q.credits} <small>积分 · 演示</small></strong></div><p>${esc(Object.values(d.parameters[d.agent]).join(' / '))}</p>${source?`<div class="notice">${source.copy}</div>`:''}<div class="notice">完整成果保存后消费；确定失败释放。</div>${helpDetails('查看完整提交内容',`<p class="preserve-lines">${esc(Demo.productText(d.productDetails))}</p><p class="preserve-lines">指令：${esc(d.prompt||'按商品资料生成')}<br>素材：${esc(d.material?.name||'无')}<br>规格 ${q.specVersion} / 价格 ${q.priceVersion}${d.sourceTaskId?`<br>来源任务 ${esc(d.sourceTaskId)}`:''}</p>`)}`,'确认并冻结积分',()=>{try{const t=Demo.admit(conversationId,submitted,key);selectedTaskId=t.id;Demo.state.currentId=conversationId;go('workspace');render();toast(`${t.id} 已受理，冻结 ${q.credits} 积分。`)}catch(e){return e.message}});
}
function showSnapshot(t) {
  const s=t.snapshot;
  dialog('本次输入快照',`<p>任务 ${t.id} · 会话 ${t.conversationId} · Agent ${s.agentVersion}</p><dl class="snapshot"><dt>商品资料</dt><dd>${esc(s.product)}</dd><dt>创作指令</dt><dd>${esc(s.instruction||'（空）')}</dd><dt>素材标识 / 版本</dt><dd>${esc(s.material?`${s.material.id} / ${s.material.version} / ${s.material.name}`:'无（可选）')}</dd><dt>全部参数</dt><dd>${Object.entries(s.parameters).map(([k,v])=>`${esc(parameterOptions[s.agent][k][0])}：${esc(v)}`).join('<br>')}</dd><dt>费用 / 版本</dt><dd>${s.quote.credits} 积分 · ${s.quote.specVersion} / ${s.quote.priceVersion}</dd>${s.sourceTaskId?`<dt>重新生成来源</dt><dd>${s.sourceTaskId}</dd>`:''}</dl>`,'关闭',()=>{});
}
function taskDetail(t) {
  const s=t.snapshot;
  const labels={success:'成功',pending:'待核查',saving:'保存失败待恢复',failed:'失败',running:'执行中',partial:'执行中 · 临时文案片段'};
  const settlement={frozen:'冻结中',consumed:'已消费',released:'已释放'};
  openOverlay({title:`任务详情 · ${t.id}`,drawer:true,body:`<dl class="snapshot"><dt>状态 / 积分</dt><dd>${labels[t.status]} · ${settlement[t.settlement]} · ${s.quote.credits} 积分</dd><dt>会话 / Agent</dt><dd>${t.conversationId} / ${names[s.agent]} / ${s.agentVersion}</dd><dt>规格 / 价格版本</dt><dd>${s.quote.specVersion} / ${s.quote.priceVersion}</dd></dl><h3>任务记录</h3><ol class="admin-timeline">${t.events.map(x=>`<li>${esc(x.note)}</li>`).join('')}</ol><details class="settings-disclosure"><summary>查看提交时的输入快照</summary><dl class="snapshot"><dt>商品资料</dt><dd>${esc(s.product)}</dd><dt>指令</dt><dd>${esc(s.instruction||'按商品资料生成')}</dd><dt>素材</dt><dd>${esc(s.material?`${s.material.name} / ${s.material.id} / ${s.material.version}`:'无')}</dd><dt>生成设置</dt><dd>${Object.entries(s.parameters).map(([k,v])=>`${esc(parameterOptions[s.agent][k][0])}：${esc(v)}`).join('<br>')}</dd><dt>提交标识</dt><dd>${esc(t.submissionKey)}</dd>${s.sourceTaskId?`<dt>重新生成来源</dt><dd>${s.sourceTaskId}</dd>`:''}</dl></details>${taskButton('查看来源会话','open-task',t.id)}${helpDetails('任务规则说明','<p>受理不明先核查原任务；保存失败仅恢复原结果，不重发生成。原任务快照保持不变。本地演示不代表服务端恢复已实现。</p>')}`});
}
function previewTask(t) {
  const r=resultOf(t);if(!r){toast('尚无正式完整成果。');return}
  dialog(`作品预览 · ${t.id} · 人工演示`,r.type==='image'?`<img src="${r.asset}" alt="人工演示版式样例" style="width:100%">`:r.type==='video'?`<video controls preload="metadata" src="${r.asset}" aria-label="人工演示视频"></video><p><small>约2秒原型短片，不代表5秒规格或真实 Agent 能力。</small></p>`:`<p class="preserve-lines">${esc(r.text)}</p>`,'关闭',()=>{});
}
async function copyTask(t) {
  const r=resultOf(t);if(!r||r.type!=='text')return;
  try{await navigator.clipboard.writeText(r.text);toast('演示文案已复制。')}catch{dialog('复制文案',`<textarea aria-label="可复制文案">${esc(r.text)}</textarea>`,'关闭',()=>{})}
}
function downloadTask(t) {
  const r=resultOf(t);if(!r)return;
  const a=document.createElement('a'),url=r.type==='text'?URL.createObjectURL(new Blob([r.text],{type:'text/plain;charset=utf-8'})):r.asset;
  a.href=url;a.download=`${t.id}-人工演示.${r.type==='text'?'txt':r.type==='image'?'png':'webm'}`;a.click();if(r.type==='text')setTimeout(()=>URL.revokeObjectURL(url),1000);toast('已下载人工演示样例；生产下载需权限校验。');
}
function openTask(t) {Demo.state.currentId=t.conversationId;selectedTaskId=t.id;pendingScroll=`[data-task-id="${t.id}"]`;if(location.hash==='#workspace'){render();$(pendingScroll)?.scrollIntoView();pendingScroll=null;}else go('workspace')}
function regenerate(t) {Demo.restoreInput(t.id);pendingScroll='#composer';if(location.hash==='#workspace'){render();$('#composer')?.scrollIntoView();pendingScroll=null;}else go('workspace');toast(`已带回 ${t.id} 原输入，请检查素材并确认新报价。`)}
async function handleClick(e) {
  const b=e.target.closest('[data-action]');if(!b)return;
  if(typeof AdminDemo!=='undefined'&&AdminDemo.handle(b))return;
  const action=b.dataset.action,t=b.dataset.taskId?Demo.task(b.dataset.taskId):null,d=draft();
  if(['home','workspace','works','account','recharge','login','register'].includes(action)){go(action);return}
  if(action==='session'){Demo.state.currentId=b.dataset.conversationId;selectedTaskId=null;render();document.querySelector('[data-action="session"][data-conversation-id="'+b.dataset.conversationId+'"]')?.focus();return}
  if(action==='new-session'||action==='demo-empty'){Demo.createConversation();selectedTaskId=null;render();$('#prompt')?.focus();return}
  if(action.startsWith('agent-')){d.agent=action.slice(6);render();document.querySelector('[data-action="'+action+'"]')?.focus();return}
  if(action.startsWith('admin-')){adminTab=action.slice(6);render();document.querySelector('[data-action="'+action+'"]')?.focus();return}
  if(action.startsWith('filter-')){filter=action.slice(7);render();document.querySelector('[data-action="'+action+'"]')?.focus();return}
  if(action.startsWith('auth-')){authTab=action.slice(5);if(location.hash==='#register')go('login');render();return}
  if(action.startsWith('demo-')) {
    const s=action.slice(5);
    if(s==='quote'){d.quoteStale=true;toast('已模拟旧报价失效，点击生成重新确认。');return}
    if(s==='material-missing'){if(d.material)d.material.available=false;render();toast('仅当前草稿模拟素材缺失，已受理快照不变。');return}
    if(s==='reset'||s==='insufficient'){Demo.reset(s==='reset'?'normal':'insufficient');selectedTaskId=null;filter='all';render();toast('已加载另一完整本地场景；全部任务/账户/流水同步重置。');return}
    const outcome=Demo.transition(selectedTaskId,s);render();if(!outcome.ok)toast(outcome.message);return;
  }
  if(action==='assist'){if(!d.productDetails.name.trim()){toast('请先填写商品名称，辅助不创建任务。');editProduct();return}d.preview=`${Demo.productText(d.productDetails)}\n${d.prompt}\n${d.agent==='text'?'仅使用已知资料整理通用电商文案，不补充功效、材质或优惠。':d.agent==='image'?'以商品为主体，保持参考素材商品特征，不添加未提供的促销信息。':`围绕已知商品场景准备画面与节奏。规格：${Object.values(d.parameters.video).join(' / ')}。不补充商品事实。`}`;render();$('#preview-prompt')?.focus();return}
  if(action==='edit-product'){editProduct();return}
  if(action==='choose-material'){$('#material').click();return}
  if(action==='edit-profile'){editProfile();return}
  if(action==='ledger-detail'){ledgerDetail(b.dataset.ledgerId);return}
  if(action==='account-detail'){const p=Demo.state.profile;openOverlay({title:'账号详情',drawer:true,body:'<dl class="snapshot">'+[['用户编号',p.id],['账号',p.username],['角色',p.role],['状态',p.status],['注册时间',p.registeredAt],['最近登录',p.lastLoginAt]].map(([k,v])=>'<dt>'+k+'</dt><dd>'+esc(v)+'</dd>').join('')+'</dl><p class="muted">账号恢复方案待确认，当前资料均为演示。</p>'});return}
  if(action==='apply-prompt'){if(d.preview===null)return;d.undo=d.prompt;d.prompt=d.preview;d.preview=null;render();$('#prompt')?.focus();toast('已采用建议，可继续编辑或撤回。');return}
  if(action==='cancel-prompt'){d.preview=null;render();$('[data-action="assist"]')?.focus();return}
  if(action==='undo-prompt'){if(d.undo===null)return;d.prompt=d.undo;d.undo=null;d.preview=null;render();$('#prompt')?.focus();toast('已恢复原指令。');return}
  if(action==='generate'){feeConfirm();return}
  if(t){
    if(action==='snapshot'){showSnapshot(t);return}if(action==='task-preview'){previewTask(t);return}if(action==='task-copy'){await copyTask(t);return}if(action==='task-download'){downloadTask(t);return}
    if(action==='task-regenerate'||action==='edit-task'){regenerate(t);return}if(action==='open-task'){openTask(t);return}
    if(action==='task-detail'){taskDetail(t);return}
  }
  if(action==='delete-work'){const id=b.dataset.workId,w=Demo.state.works.find(x=>x.id===id);dialog('删除作品',`<p>确定从演示列表中删除“${esc(w?.name)}”吗？</p><p>任务与积分记录保留。生产删除与恢复政策待确认。</p>`,'确认删除',()=>{Demo.state.works=Demo.state.works.filter(w=>w.id!==id);render();toast('已移出演示列表。')},{danger:true});return}
  handleAdmin(action);
}
function handleAdmin(action) {
  if(action==='investigate'){dialog('核查原任务 A-T-1041','<p>后台独立诊断 fixture，非个人账户任务。外部标识保留；受理不明须核查原任务，不盲目重发。</p><div class="notice warn">D-08 未确认时人工结算与释放禁用。</div>','记录核查示例',()=>toast('仅展示后台诊断，不改变个人账户。'));return}
  if(action==='recover'){dialog('恢复原结果保存 A-T-1040','<p>后台独立诊断 fixture。只恢复原结果保存，不调用生成、不新增冻结。完整入库前保持冻结。</p>','查看恢复示例',()=>toast('原结果 → 保存 → 入库 → 唯一结算；当前仅诊断示例。'));return}
  if(action==='private'){dialog('申请独立内容授权','<p>当前管理员没有内容访问授权。记录范围、对象、原因、有效期、操作人与时间；申请不会授予权限。</p><label for="access-reason">访问原因</label><textarea id="access-reason"></textarea>','登记申请演示',()=>toast('演示申请已登记，私有内容仍隐藏。'));return}
  if(action==='grant') {
    if(!$('#credit-reason').value.trim()){$('#credit-error').textContent='请填写发放原因，未执行发放。';$('#credit-reason').focus();return}if(Number($('#credit-amount').value)<=0){$('#credit-error').textContent='积分数量必须大于 0。';return}
    dialog('确认模拟发放',`<p>账户：${esc($('#credit-user').value)}<br>数量：${esc($('#credit-amount').value)}<br>原因：${esc($('#credit-reason').value)}<br>操作人：admin-demo</p>`,'记录发放演示',()=>toast('仅确认后台独立示例，未改变个人账户。'));return;
  }
  if(action==='task-filter'){document.querySelectorAll('[data-task-status]').forEach(r=>r.hidden=$('#task-filter').value!=='全部任务'&&r.dataset.taskStatus!==$('#task-filter').value);return}
  if(action==='price-save'){dialog('发布模拟价格版本','<p>仅影响后续报价；已受理任务保留原价格。此处为后台独立演示，不改变个人任务。</p>','确认模拟发布',()=>toast('已展示版本发布流程。'));return}
  if(action==='logout'){toast('已退出演示账户，生产退出需撤销登录会话。');go('login');return}
  toast({'save-profile':'演示资料已展示，未连接账户服务。','save-config':'模拟配置已展示；生产写入需权限、版本和审计。','user-detail':'后台独立账户 fixture，无密码哈希或私有正文。'}[action]||'演示操作已展示。');
}
document.addEventListener('click',e=>{if(e.target.closest('#dialog [data-action]')){closeOverlay();handleClick(e)}else handleClick(e)});
window.addEventListener('hashchange',()=>{render();if(pendingScroll){$(pendingScroll)?.scrollIntoView();pendingScroll=null;}else window.scrollTo(0,0)});
render();
