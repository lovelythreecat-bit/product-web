// One in-memory demonstration model. It does not implement a server ledger.
const Demo = (() => {
  const names = {text:'文案', image:'图片', video:'视频'};
  const prices = {text:8, image:20, video:60};
  const defaults = {
    text:{length:'通用短文 · 演示能力',tone:'简洁自然'},
    image:{purpose:'商品主图',ratio:'1:1 / 1024px · 演示',style:'简洁棚拍 · 演示',count:'1 张'},
    video:{duration:'5 秒 · 演示档位',ratio:'竖屏 9:16',resolution:'720p · 演示',voice:'无配音',captions:'不添加',music:'无音乐'}
  };
  const clone = v => JSON.parse(JSON.stringify(v));
  const productFields = [
    ['name','商品名称'],['category','商品品类'],['brand','品牌'],['model','型号 / SKU'],
    ['material','材质'],['color','颜色'],['size','尺寸'],['weight','重量'],
    ['capacity','容量 / 净含量'],['package','包装清单'],['sellingPoints','核心卖点'],
    ['audience','适用人群'],['scene','使用场景'],['notes','补充说明']
  ];
  const emptyProduct = () => Object.fromEntries(productFields.map(([key])=>[key,'']));
  const productText = details => productFields.filter(([key])=>String(details[key]||'').trim())
    .map(([key,label])=>key==='name'?String(details[key]).trim():`${label}：${String(details[key]).trim()}`).join('\n');
  function immutable(v) {
    Object.values(v).forEach(x=>{if(x && typeof x==='object') immutable(x)});
    return Object.freeze(v);
  }
  function newDraft(details={}, material=null) {
    const productDetails={...emptyProduct(),...details};
    return {agent:'text', product:productText(productDetails), productDetails, prompt:'', material, parameters:clone(defaults),
      priceVersion:'demo-p1', quoteStale:false, preview:null, undo:null, sourceTaskId:null};
  }
  let state;
  const current = () => state.conversations.find(c=>c.id===state.currentId);
  const task = id => state.tasks.find(t=>t.id===id);
  const quote = d => ({credits:prices[d.agent], specVersion:'demo-s1', priceVersion:d.priceVersion, agentVersion:`demo-${d.agent}-v1`});
  const accountView = () => clone(state.account);
  function ledger(kind, amount, taskId, before, note) {
    state.ledger.push({id:`L-${state.ledger.length+1}`,kind,amount,taskId,before,after:accountView(),
      at:new Date().toLocaleTimeString('zh-CN',{hour12:false}),note});
  }
  function validate(d) {
    if(!String(d.productDetails?.name||'').trim()) return '请填写商品名称，未创建任务或冻结积分。';
    if(d.agent!=='text' && (!d.material || !d.material.available)) return '当前演示规格需要商品图片；原素材缺失，请重新选择素材，未受理或冻结。';
    if(d.quoteStale) return '报价已失效，请重新确认当前报价。';
    if(state.account.available<prices[d.agent]) return '积分不足，任务未创建。';
    return null;
  }
  function admit(conversationId, submittedDraft, key) {
    const fingerprint=JSON.stringify({agent:submittedDraft.agent,product:productText(submittedDraft.productDetails),productDetails:submittedDraft.productDetails,prompt:submittedDraft.prompt,
      material:submittedDraft.material,parameters:submittedDraft.parameters[submittedDraft.agent],quote:quote(submittedDraft)});
    const old=state.tasks.find(t=>t.submissionKey===key);
    if(old) {
      if(old.fingerprint!==fingerprint) throw new Error('同一提交标识内容不一致，未受理。');
      return old;
    }
    const error=validate(submittedDraft); if(error) throw new Error(error);
    const c=state.conversations.find(c=>c.id===conversationId);
    const d=clone(submittedDraft), id=`T-${++state.taskSeq}`;
    d.product=productText(d.productDetails);
    const snapshot=immutable({agent:d.agent,agentVersion:`demo-${d.agent}-v1`,product:d.product,productDetails:d.productDetails,instruction:d.prompt,
      material:d.material,parameters:d.parameters[d.agent],quote:quote(d),sourceTaskId:d.sourceTaskId});
    const t={id,conversationId:c.id,submissionKey:key,fingerprint,snapshot,status:'running',settlement:'frozen',
      events:[{status:'running',note:'用户已确认报价，本地受理并冻结一次。'}],workId:null};
    const before=accountView(); state.account.available-=snapshot.quote.credits; state.account.frozen+=snapshot.quote.credits;
    state.tasks.push(t); c.taskIds.push(id); c.title=d.product.split('\n')[0].slice(0,26)||c.title;
    ledger('任务冻结',snapshot.quote.credits,id,before,'确认报价后受理；固定费用快照。');
    return t;
  }
  function resultFor(t) {
    return {type:t.snapshot.agent,text:`人工演示文案 / 非真实 AI 产出\n${t.snapshot.product}\n创作要求：${t.snapshot.instruction||'根据已提供资料整理商品介绍。'}`,
      asset:t.snapshot.agent==='image'?'assets/sample-image.png':t.snapshot.agent==='video'?'assets/sample-video.webm':null};
  }
  function publish(t) {
    if(t.workId) return;
    const id=`W-${t.id.slice(2)}`;
    state.works.push({id,taskId:t.id,conversationId:t.conversationId,type:t.snapshot.agent,
      name:`${t.snapshot.product.split('\n')[0].slice(0,24)} · ${names[t.snapshot.agent]}成果`,result:resultFor(t)});
    t.workId=id;
  }
  function transition(id, status) {
    const t=task(id); if(!t) return {ok:false,message:'请先确认费用并生成一个任务。'};
    if(t.settlement!=='frozen') return {ok:false,message:'任务已完成结算，终态保持；重复操作不再扣减或释放。'};
    if(status==='partial' && t.snapshot.agent!=='text') return {ok:false,message:'临时文案片段仅适用于文案任务。'};
    const amount=t.snapshot.quote.credits, before=accountView();
    if(status==='success') {
      publish(t); state.account.frozen-=amount; state.account.consumed+=amount; t.settlement='consumed';
      ledger('成功结算',amount,id,before,'完整人工演示成果已加入本地作品库，唯一结算。');
    } else if(status==='failed') {
      state.account.frozen-=amount; state.account.available+=amount; t.settlement='released';
      ledger('确定失败释放',amount,id,before,'模拟接口明确失败；释放全部固定费用。');
    }
    t.status=status;
    t.events.push({status,note:{pending:'受理不明，核查原任务，保持冻结。',saving:'原结果已定位，恢复原结果保存，保持冻结。',
      success:'完整结果入库并结算。',failed:'确定失败并释放。',partial:'临时片段不属于作品，不结算。',running:'恢复原任务执行，不新冻结。'}[status]});
    return {ok:true};
  }
  function createConversation() {
    const c={id:`C-${++state.conversationSeq}`,title:'新会话',draft:newDraft(),taskIds:[]};
    state.conversations.push(c); state.currentId=c.id; return c;
  }
  function restoreInput(id) {
    const t=task(id); if(!t) return false;
    const d=current().draft, s=t.snapshot;
    d.agent=s.agent; d.product=s.product; d.productDetails=clone(s.productDetails); d.prompt=s.instruction; d.material=clone(s.material);
    d.parameters[s.agent]=clone(s.parameters); d.sourceTaskId=id; d.preview=null; d.undo=null;
    // Keep the editor's current quote version: active regeneration requires a new quote.
    return true;
  }
  function reset(kind='normal') {
    state={account:{available:200,frozen:0,consumed:0,credited:200},
      profile:{id:'U-1001',username:'demo-shop',role:'普通用户',status:'正常',registeredAt:'2026-10-09 10:20',lastLoginAt:'2026-10-11 09:10',
        nickname:'青瓷小店',shopName:'青瓷小店',category:'家居日用',email:'',phone:'',bio:''},ledger:[],tasks:[],works:[],
      currentId:'C-1',conversationSeq:2,taskSeq:1040,conversations:[
        {id:'C-1',title:'青瓷马克杯',draft:newDraft({name:'青瓷马克杯',capacity:'350mL',package:'带杯盖',scene:'办公室日常饮水'},{id:'demo-cup',version:'v1',name:'product-cup.jpg · 演示素材',available:true}),taskIds:[]},
        {id:'C-2',title:'桌面收纳盒',draft:newDraft({name:'桌面收纳盒',size:'20cm',color:'蓝色'},{id:'demo-box',version:'v1',name:'storage-box.jpg · 演示素材',available:true}),taskIds:[]} ]};
    state.conversations[0].draft.prompt='写一段简洁的商品介绍，重点描述使用场景。';
    ledger('注册赠送',200,null,{available:0,frozen:0,consumed:0,credited:0},'账户 demo-shop · 一次性测试入账，非支付收入。');
    for(const a of ['text','image','video']) {
      const d=clone(current().draft); d.agent=a;
      const t=admit('C-1',d,`baseline-${a}`); transition(t.id,'success');
    }
    if(kind==='insufficient') {
      const before=accountView(),amount=state.account.available;
      // A separate explicitly loaded zero-credit fixture; all values and ledger remain consistent.
      state.account.available=0; state.account.credited-=amount;
      ledger('演示入账撤销',-amount,null,before,'仅加载低余额 fixture；非产品功能或真实账户操作。');
    }
  }
  reset();
  return {names,prices,defaults,productFields,productText,clone,current,task,quote,validate,admit,transition,createConversation,restoreInput,reset,
    get state(){return state}};
})();
