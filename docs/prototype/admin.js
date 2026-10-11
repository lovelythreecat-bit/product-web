// Independent, in-memory admin fixtures. Never writes to the personal Demo model.
const AdminDemo = (() => {
  const safe = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const now = () => new Date().toLocaleString('zh-CN', {hour12:false});
  const state = {
    selectedTask:null, selectedUser:null, taskQuery:'', taskStatus:'全部', taskAgent:'全部',
    userQuery:'', userStatus:'全部', creditQuery:'', logQuery:'', logType:'全部', gift:200,
    users:[
      {id:'U-A028',account:'admin-fixture',nickname:'青瓷商铺',shop:'青瓷生活',contact:'陈店长',email:'shop@example.invalid',role:'普通用户',status:'正常',joined:'2026-10-08 10:20',lastLogin:'2026-10-11 09:40',tasks:12,available:180,frozen:60,consumed:88,deleted:false},
      {id:'U-A016',account:'storage-fixture',nickname:'桌面收纳',shop:'收纳实验室',contact:'林店长',email:'storage@example.invalid',role:'普通用户',status:'正常',joined:'2026-10-09 11:30',lastLogin:'2026-10-11 08:15',tasks:8,available:120,frozen:20,consumed:72,deleted:false},
      {id:'U-A003',account:'reviewer-fixture',nickname:'内容维护员',shop:'',contact:'李管理员',email:'',role:'管理员',status:'正常',joined:'2026-10-07 14:10',lastLogin:'2026-10-10 18:20',tasks:4,available:200,frozen:0,consumed:32,deleted:false}
    ],
    tasks:[
      {id:'A-T-1041',userId:'U-A028',conversation:'A-C-028',agent:'视频',status:'待核查',settlement:'冻结中',cost:60,duration:'12 分钟',started:'2026-10-11 09:28',updated:'2026-10-11 09:40',external:'ext-video-1041',upstream:'尚未取得可验证 ID',error:'提交响应丢失，是否受理未知',work:'尚未正式入库',events:['09:28 接受报价并冻结 60 积分','09:29 向上游提交，保留外部标识','09:30 提交响应丢失，转待核查；未重发、未结算']},
      {id:'A-T-1040',userId:'U-A016',conversation:'A-C-016',agent:'图片',status:'保存失败待恢复',settlement:'冻结中',cost:20,duration:'6 分钟',started:'2026-10-11 09:34',updated:'2026-10-11 09:40',external:'ext-image-1040',upstream:'img-demo-1040',error:'本地存储容量不足，原结果定位已保留',work:'保存记录 A-S-1040；未发布作品',events:['09:34 接受报价并冻结 20 积分','09:36 上游结果已取得，进入结果保存','09:40 保存失败，保留原结果定位；不重新生成']},
      {id:'A-T-1039',userId:'U-A028',conversation:'A-C-028',agent:'文案',status:'成功',settlement:'已消费',cost:8,duration:'18 秒',started:'2026-10-11 09:10',updated:'2026-10-11 09:10',external:'ext-text-1039',upstream:'txt-demo-1039',error:'无异常',work:'A-W-203 · 内容隐藏',events:['09:10 接受报价并冻结 8 积分','09:10 完整成果与作品保存完成','09:10 唯一结算，已消费 8 积分']},
      {id:'A-T-1038',userId:'U-A016',conversation:'A-C-016',agent:'文案',status:'失败',settlement:'已释放',cost:8,duration:'22 秒',started:'2026-10-10 17:10',updated:'2026-10-10 17:11',external:'ext-text-1038',upstream:'txt-demo-1038',error:'模拟上游已明确返回失败',work:'无正式作品',events:['17:10 接受报价并冻结 8 积分','17:11 明确失败，全部释放 8 积分']}
    ],
    agents:[
      {id:'text',name:'文案 Agent',endpoint:'https://text.example.invalid/api',version:'demo-v1',status:'模拟启用',stream:'模拟支持',result:'完整文案',query:'待 D-01 确认'},
      {id:'image',name:'图片 Agent',endpoint:'https://image.example.invalid/api',version:'demo-v1',status:'模拟启用',stream:'不适用',result:'单张图片',query:'待 D-01 确认'},
      {id:'video',name:'视频 Agent',endpoint:'https://video.example.invalid/api',version:'demo-v1',status:'模拟启用',stream:'不适用',result:'完整视频',query:'待 D-01 确认'}
    ],
    specs:[
      {id:'text-s1',agent:'文案',name:'通用短文 1 份',params:'通用短文 / 简洁自然 / 1 份',price:8,version:1,status:'模拟启用'},
      {id:'image-s1',agent:'图片',name:'商品主图 1 张',params:'1:1 / 1024px / 简洁棚拍 / 1 张',price:20,version:1,status:'模拟启用'},
      {id:'video-s1',agent:'视频',name:'竖屏视频',params:'5 秒 / 9:16 / 720p / 无配音',price:60,version:1,status:'模拟启用'}
    ],
    ledger:[{id:'A-L-018',at:'2026-10-10 14:20',userId:'U-A028',account:'admin-fixture',kind:'管理员发放',amount:50,before:130,after:180,reason:'联调试用',operator:'admin-demo'}, {id:'A-L-017',at:'2026-10-09 10:20',userId:'U-A016',account:'storage-fixture',kind:'注册赠送',amount:200,before:0,after:200,reason:'一次性模拟注册赠送',operator:'系统演示'}],
    logs:[{id:'A-O-001',at:'2026-10-10 14:20',kind:'积分发放',object:'U-A028',note:'+50 积分 · 联调试用',operator:'admin-demo'}, {id:'A-O-002',at:'2026-10-10 13:40',kind:'配置修改',object:'text-s1',note:'模拟价格版本 demo-p1；已受理任务保留快照',operator:'admin-demo'}],
    intro:'围绕商品资料，完成文案、图片和视频创作。', userSeq:28, logSeq:2, ledgerSeq:18
  };
  function audit(kind,object,note) {state.logs.unshift({id:`A-O-${++state.logSeq}`,at:now(),kind,object,note,operator:'admin-demo'});}
  const button = (text, action, id='', cls='') => `<button type="button" class="${cls}" data-action="manage-${action}" data-manage-id="${safe(id)}">${text}</button>`;
  const tag = (text, cls='') => `<span class="pill ${cls}">${safe(text)}</span>`;
  const options = (items,current) => items.map(x=>`<option ${x===current?'selected':''}>${safe(x)}</option>`).join('');
  const field = (label,name,value='',type='text',extra='') => `<div class="field"><label for="manage-${name}">${label}</label><input id="manage-${name}" name="${name}" type="${type}" value="${safe(value)}" ${extra}></div>`;
  const select = (label,name,items,value) => `<div class="field"><label for="manage-${name}">${label}</label><select id="manage-${name}" name="${name}">${options(items,value)}</select></div>`;
  const table = (heads,rows,empty='暂无符合条件的记录') => `<div class="table-wrap"><table><thead><tr>${heads.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.join(''):`<tr><td colspan="${heads.length}" class="empty-state">${empty}</td></tr>`}</tbody></table></div>`;
  const summary = items => `<div class="admin-summary">${items.map(([label,value,desc])=>`<div><small>${label}</small><strong>${value}</strong><span class="muted">${desc||'后台独立演示'}</span></div>`).join('')}</div>`;
  const heading = (title,desc,action='') => `<div class="row spread wrap"><div><h2>${title}</h2><p class="muted">${desc}</p></div>${action}</div>`;
  const detail = items => `<dl class="detail-grid">${items.map(([label,value])=>`<div><dt>${label}</dt><dd>${safe(value)}</dd></div>`).join('')}</dl>`;
  function user(id) {return state.users.find(u=>u.id===id);}
  function activeUsers() {return state.users.filter(u=>!u.deleted);}
  function filterTasks() {return state.tasks.filter(t=>(state.taskStatus==='全部'||t.status===state.taskStatus)&&(state.taskAgent==='全部'||t.agent===state.taskAgent)&&`${t.id} ${t.userId} ${user(t.userId)?.account}`.toLowerCase().includes(state.taskQuery.toLowerCase()));}
  function tasksView() {
    const t=state.tasks.find(x=>x.id===state.selectedTask);
    if(t) return `<div class="admin-detail">${detail([['平台任务 ID',t.id],['所属用户',`${t.userId} / ${user(t.userId)?.account}`],['会话 ID',t.conversation],['任务状态',t.status],['结算状态',t.settlement],['固定费用',`${t.cost} 积分 · 演示值`],['Agent / 接入版本',`${t.agent} / demo-v1`],['规格 / 价格版本','demo-s1 / demo-p1'],['开始 / 更新时间',`${t.started} / ${t.updated}`],['累计耗时',t.duration],['外部提交标识',t.external],['上游任务 ID',t.upstream],['关联成果 / 保存记录',t.work],['必要错误信息',t.error]])}</div><section class="admin-section"><h3>任务时间线</h3><ol class="admin-timeline">${t.events.map(e=>`<li>${safe(e)}</li>`).join('')}</ol></section><div class="notice">用户商品资料、素材、创作指令与作品正文默认隐藏。查看内容需要独立授权并记录访问原因。</div><div class="row wrap" style="margin-top:16px">${button('申请内容查看授权','access',t.id)}</div>${t.status==='待核查'?'<section class="admin-section"><h3>核查记录</h3><p>沿用原任务与外部标识核查是否受理；暂无可靠查单证据，不盲目重发。</p></section>':t.status==='保存失败待恢复'?'<section class="admin-section"><h3>保存恢复记录</h3><p>原结果定位已保留；后续只恢复下载与保存，不调用新生成、不新增冻结。完整入库后才可结算。</p></section>':''}<div class="notice warn" style="margin-top:18px">D-08 未确认，人工结算和释放尚未开放。期限届满不证明失败；没有完整交付证据不得结算。</div>`;
    const rows=filterTasks();
    return `${heading('任务与异常','按任务、用户、Agent 和状态定位记录；查看详情可见诊断时间线。')}${summary([['任务记录',state.tasks.length],['待核查',state.tasks.filter(t=>t.status==='待核查').length],['保存待恢复',state.tasks.filter(t=>t.status==='保存失败待恢复').length],['冻结积分',state.tasks.filter(t=>t.settlement==='冻结中').reduce((a,t)=>a+t.cost,0)]])}<form class="admin-toolbar" data-manage-form="tasks">${field('任务 / 用户','taskQuery',state.taskQuery,'search','placeholder="任务 ID、用户 ID 或账号"')}${select('任务状态','taskStatus',['全部','待核查','保存失败待恢复','成功','失败'],state.taskStatus)}${select('Agent','taskAgent',['全部','文案','图片','视频'],state.taskAgent)}<button class="primary">查询</button>${button('清空','task-clear')}</form>${table(['任务 / 用户','状态 / 结算','Agent / 耗时','费用 / 必要错误信息','查看'],rows.map(t=>`<tr><td>${t.id}<br><small>${t.userId} · ${safe(user(t.userId)?.account)}</small></td><td>${tag(t.status,t.settlement==='冻结中'?'warn':t.status==='失败'?'error':'')}<br>${t.settlement}</td><td>${t.agent} · demo-v1<br><small>${t.duration}</small></td><td>${t.cost} 积分 · demo-p1<br><small>${safe(t.error)}</small></td><td>${button('查看','task-view',t.id)}</td></tr>`))}<p><small>显示 ${rows.length} / ${state.tasks.length} 条 · 后台独立诊断样例；私有内容隐藏，任务与结算分别记录。</small></p>`;
  }
  function usersView() {
    const u=user(state.selectedUser);
    if(u&&!u.deleted) return `${summary([['累计生成任务',u.tasks],['可用积分',u.available],['冻结积分',u.frozen],['累计消费',u.consumed]])}<div class="admin-detail">${detail([['账号',u.account],['昵称',u.nickname],['店铺名称',u.shop||'未填写'],['联系人',u.contact||'未填写'],['联系邮箱',u.email||'未填写'],['角色',u.role],['状态',u.status],['注册时间',u.joined],['最近登录',u.lastLogin],['最近密码重置',u.resetAt||'暂无演示记录']])}</div><div class="row wrap">${button('编辑资料','user-edit',u.id)}${button('重置密码','user-reset',u.id)}${button('删除用户','user-delete',u.id,'danger')}</div><section class="admin-section"><h3>关联任务</h3>${table(['任务','Agent','状态 / 结算','查看'],state.tasks.filter(t=>t.userId===u.id).map(t=>`<tr><td>${t.id}</td><td>${t.agent}</td><td>${t.status} / ${t.settlement}</td><td>${button('查看','task-view',t.id)}</td></tr>`),'此演示用户暂无关联任务')}</section><p><small>不显示密码、密码哈希或私有内容。联系信息可选，不作为注册验证前置。</small></p>`;
    const rows=activeUsers().filter(u=>(state.userStatus==='全部'||u.status===state.userStatus)&&`${u.account} ${u.id} ${u.nickname} ${u.shop}`.toLowerCase().includes(state.userQuery.toLowerCase()));
    return `${heading('用户管理','维护账号资料、角色和状态，查询用量与积分。',button('新增用户','user-add','','primary'))}${summary([['用户数',activeUsers().length],['正常账号',activeUsers().filter(u=>u.status==='正常').length],['管理员',activeUsers().filter(u=>u.role==='管理员').length],['已删除演示记录',state.users.filter(u=>u.deleted).length]])}<form class="admin-toolbar" data-manage-form="users">${field('搜索用户','userQuery',state.userQuery,'search','placeholder="账号、用户 ID、昵称或店铺"')}${select('账户状态','userStatus',['全部','正常','停用'],state.userStatus)}<button class="primary">查询</button>${button('清空','user-clear')}</form>${table(['账号 / 用户 ID','昵称 / 店铺','角色 / 状态','注册 / 最近登录','任务 / 可用 / 冻结','操作'],rows.map(u=>`<tr><td>${safe(u.account)}<br><small>${u.id}</small></td><td>${safe(u.nickname)}<br><small>${safe(u.shop||'未填写店铺')}</small></td><td>${safe(u.role)}<br>${tag(u.status,u.status==='停用'?'warn':'')}</td><td>${u.joined}<br><small>${u.lastLogin}</small></td><td>${u.tasks} 次<br><small>${u.available} / ${u.frozen} 积分</small></td><td><div class="row wrap">${button('查看','user-view',u.id)}${button('编辑','user-edit',u.id)}<details class="action-menu"><summary>更多</summary><div>${button('重置密码','user-reset',u.id)}${button('删除用户','user-delete',u.id,'danger')}</div></details></div></td></tr>`))}<p><small>显示 ${rows.length} / ${activeUsers().length} 个用户。新增、编辑、删除和重置仅在此后台演示数据中生效，刷新重置。</small></p><div class="notice warn" style="margin-top:18px">删除仅隐藏演示用户，保留任务、积分和审计记录；生产删除与停用政策待 D-09 确认。密码恢复的身份核验、权限和审计方案待 D-07 确认。</div>`;
  }
  function creditsView() {
    const rows=state.ledger.filter(l=>String(l.userId+' '+l.account+' '+l.reason).toLowerCase().includes(state.creditQuery.toLowerCase()));
    return heading('积分管理','查询积分流水，按需配置赠送或发放。',button('发放积分','grant-open','','primary'))+summary([['注册赠送',state.gift,'仅影响后续演示新账号'],['可用积分',activeUsers().reduce((n,u)=>n+u.available,0)],['冻结积分',activeUsers().reduce((n,u)=>n+u.frozen,0)],['流水记录',state.ledger.length]])+'<div class="row wrap admin-section">'+button('配置注册赠送','gift-edit')+'</div><h3>积分流水</h3><form class="admin-toolbar" data-manage-form="credits">'+field('查询账户 / 原因','creditQuery',state.creditQuery,'search')+'<button class="primary">查询</button>'+button('清空','credit-clear')+'</form>'+table(['流水 / 时间','接收账户','类型 / 数量','可用积分变更','操作人 / 原因'],rows.map(l=>'<tr><td>'+l.id+'<br><small>'+l.at+'</small></td><td>'+safe(l.account)+'<br><small>'+l.userId+'</small></td><td>'+l.kind+'<br>+'+l.amount+'</td><td>'+l.before+' → '+l.after+'</td><td>'+l.operator+'<br><small>'+safe(l.reason)+'</small></td></tr>'))+helpDetails('积分管理说明','<p>余额与流水属于后台独立样例。赠送与发放不统计为支付收入；生产赠送政策待 D-05 确认。</p>');
  }
  function agentsView() {return `${heading('Agent 配置','分别维护三个服务的接入信息与能力；完整凭据不在浏览器保存。')}${summary([['接入服务',state.agents.length],['模拟启用',state.agents.filter(a=>a.status==='模拟启用').length],['生产联调','待确认','D-01～D-03'],['凭据','已脱敏','不回传完整秘密']])}${table(['服务 / 版本','地址 / 状态','完整结果 / 流式','查单与幂等','操作'],state.agents.map(a=>`<tr><td>${a.name}<br><small>${safe(a.version)}</small></td><td>${safe(a.endpoint)}<br>${tag(a.status)}</td><td>${a.result}<br><small>流式：${a.stream}</small></td><td>${a.query}<br><small>回调鉴权：待确认</small></td><td>${button('配置','agent-edit',a.id)}</td></tr>`))}<details class="context-help"><summary>接入检查说明</summary><p>完整结果获取、可靠幂等、外部标识查单、回调来源校验和输入限制须逐服务确认。凭据状态仅示意，原型不提供秘密输入。</p></details><div class="notice warn">缺少可靠查询或幂等证据时，受理不明保持待核查，不盲目重发。配置变更仅影响此处演示，个人工作台配置保持独立。</div>`;}
  function specsView() {return `${heading('规格与价格','维护参数组合与演示价格，发布新版本后保留历史任务快照。')}${summary([['模拟规格',state.specs.length],['文案起价',`${state.specs[0].price} 积分`],['图片起价',`${state.specs[1].price} 积分`],['视频起价',`${state.specs[2].price} 积分`]])}${table(['Agent / 规格','参数 / 默认值','积分价格','规格 / 价格版本','状态 / 操作'],state.specs.map(s=>`<tr><td>${s.agent}<br>${safe(s.name)}</td><td>${safe(s.params)}</td><td>${s.price} 积分</td><td>demo-s${s.version}<br>demo-p${s.version}</td><td>${tag(s.status)}<br>${button('编辑规格与价格','spec-edit',s.id)}</td></tr>`))}<details class="context-help"><summary>查看未开放规格</summary>${table(['规格','启用条件','状态'],['<tr><td>多份文案 / 多张图片 / 详情页图片</td><td>产物形态、完整交付、部分失败和计费政策待 D-04 确认</td><td><span class="pill warn">不可上架</span></td></tr>'])}</details><div class="notice warn">参数能力、范围、组合约束与生产价格待 D-02 / D-05 确认。仅发布后台模拟版本，不覆盖个人任务或已受理任务。</div>`;}
  function usageView() {
    const completed=state.tasks.filter(t=>t.status==='成功').length;
    return `${heading('用量统计','统计当前后台任务样例，所有指标均为演示数据。')}${summary([['任务总数',state.tasks.length],['成功率',`${Math.round(completed/state.tasks.length*100)}%`,'成功 / 全部任务'],['累计消费',state.tasks.filter(t=>t.settlement==='已消费').reduce((n,t)=>n+t.cost,0),'按已消费任务费用统计'],['未结算',state.tasks.filter(t=>t.settlement==='冻结中').length]])}<section class="admin-section"><h3>按 Agent 汇总</h3>${table(['Agent','任务数','成功 / 失败','未结算','消费积分'],['文案','图片','视频'].map(a=>{const ts=state.tasks.filter(t=>t.agent===a);return `<tr><td>${a}</td><td>${ts.length}</td><td>${ts.filter(t=>t.status==='成功').length} / ${ts.filter(t=>t.status==='失败').length}</td><td>${ts.filter(t=>t.settlement==='冻结中').length}</td><td>${ts.filter(t=>t.settlement==='已消费').reduce((n,t)=>n+t.cost,0)}</td></tr>`}))}</section><section class="admin-section"><h3>任务状态分布</h3><div class="row wrap">${['成功','失败','待核查','保存失败待恢复'].map(s=>tag(`${s} ${state.tasks.filter(t=>t.status===s).length}`)).join('')}</div></section><div class="notice">供应商实际用量与成本：不可获得，字段来源与口径待 D-06 确认。没有支付接入，不统计充值收入。</div>`;
  }
  function siteView() {
    return heading('官网内容','维护介绍与真实案例授权。',button('编辑产品介绍','site-edit','','primary'))+'<section class="admin-section"><h3>当前产品介绍</h3><p class="preserve-lines">'+safe(state.intro)+'</p></section><section class="admin-section"><h3>真实案例管理</h3>'+table(['案例位置','素材 / 授权','发布状态'],['<tr><td>文案案例</td><td>尚未提供真实产出及授权依据</td><td>待补充</td></tr>','<tr><td>图片案例</td><td>等待真实作品来源与授权</td><td>未发布</td></tr>','<tr><td>视频案例</td><td>等待真实作品来源与授权</td><td>未发布</td></tr>'])+'</section>'+helpDetails('公开展示规则','<p>品牌与公开文案待 D-11 确认。真实案例须记录来源、作品归属、授权与撤回流程，不默认公开私有成果。</p>');
  }
  function logsView() {
    const rows=state.logs.filter(l=>(state.logType==='全部'||l.kind===state.logType)&&`${l.object} ${l.note} ${l.operator}`.toLowerCase().includes(state.logQuery.toLowerCase()));
    return `${heading('操作日志','查询此后台演示的用户维护、积分发放与配置变更记录。')}${summary([['审计记录',state.logs.length],['用户维护',state.logs.filter(l=>l.kind==='用户维护').length],['密码重置',state.logs.filter(l=>l.kind==='密码重置').length],['配置修改',state.logs.filter(l=>l.kind==='配置修改').length]])}<form class="admin-toolbar" data-manage-form="logs">${field('对象 / 操作人 / 原因','logQuery',state.logQuery,'search')}${select('操作类型','logType',['全部','用户维护','密码重置','积分发放','配置修改','授权申请'],state.logType)}<button class="primary">查询</button>${button('清空','log-clear')}</form>${table(['记录 / 时间','操作人','操作类型 / 对象','变更或原因'],rows.map(l=>`<tr><td>${l.id}<br><small>${l.at}</small></td><td>${l.operator}</td><td>${l.kind}<br><small>${safe(l.object)}</small></td><td>${safe(l.note)}</td></tr>`))}<p><small>日志不保存密码、密码哈希、完整 Agent 凭据或用户私有正文；刷新将重置演示记录。</small></p>`;
  }
  function content(tab) {return ({tasks:tasksView,users:usersView,credits:creditsView,agents:agentsView,specs:specsView,usage:usageView,site:siteView,logs:logsView}[tab]||tasksView)().replace(/<div class="notice(?: warn)?"[^>]*>([\s\S]*?)<\/div>/g,(_,body)=>helpDetails('规则说明','<p>'+body+'</p>'));}
  function modal(title,body,submit,label='保存') {
    const modalBody=body.replace(/\b(id|for)="manage-/g,'$1="manage-modal-');
    openOverlay({title,body:modalBody,label,drawer:!/(确认|删除|重置)/.test(title),danger:/删除/.test(title),submit:(data,form)=>{
      const error=submit(data,form);if(error)return error;render();
    }});
  }
  function userForm(u) {
    return `<p class="muted">可选联系方式不增加注册验证；密码不保存在原型数据中。</p><div class="grid2">${field('账号','account',u?.account||'','text','required minlength="3" maxlength="40"')}${field('昵称','nickname',u?.nickname||'','text','required maxlength="40"')}${field('店铺名称（选填）','shop',u?.shop||'','text','maxlength="80"')}${field('联系人（选填）','contact',u?.contact||'','text','maxlength="40"')}${field('联系邮箱（选填）','email',u?.email||'','email')}${select('角色','role',['普通用户','管理员'],u?.role||'普通用户')}${select('状态 · 演示','status',['正常','停用'],u?.status||'正常')}${!u?field('初始密码 · 不保存','password','','password','required minlength="8" autocomplete="new-password"'):''}</div>${field('操作原因','reason','','text','required maxlength="160"')}<p><small>角色与停用仅更新本地演示标记。生产权限与停用政策仍需确认。</small></p>`;
  }
  function handle(b) {
    const action=b?.dataset.action;if(!action?.startsWith('manage-'))return false;
    const a=action.slice(7),id=b.dataset.manageId,u=user(id);
    if(a==='task-view'){state.selectedTask=id;const body=tasksView();state.selectedTask=null;openOverlay({title:'任务详情 · '+id,body,drawer:true});}
    else if(a==='task-back'){state.selectedTask=null;render();}
    else if(a==='task-clear'){state.taskQuery='';state.taskStatus='全部';state.taskAgent='全部';render();}
    else if(a==='user-view'){state.selectedUser=id;const body=usersView();state.selectedUser=null;openOverlay({title:'用户详情 · '+u.account,body,drawer:true});}
    else if(a==='user-back'){state.selectedUser=null;render();}
    else if(a==='user-clear'){state.userQuery='';state.userStatus='全部';render();}
    else if(a==='user-add'||a==='user-edit') modal(a==='user-add'?'新增用户 · 演示':'编辑用户 · 演示',userForm(u),data=>{
      const account=data.account.trim(),nickname=data.nickname.trim(),reason=data.reason.trim();
      if(!account||!nickname||!reason)return '请填写账号、昵称和操作原因。';
      if(state.users.some(x=>x.id!==u?.id&&x.account.toLowerCase()===account.toLowerCase()))return '账号已存在，请使用其他账号。';
      const values={account,nickname,shop:data.shop.trim(),contact:data.contact.trim(),email:data.email.trim(),role:data.role,status:data.status};
      if(u){Object.assign(u,values);audit('用户维护',u.id,`编辑资料 · ${reason}`);}
      else {const added={...values,id:`U-A${String(++state.userSeq).padStart(3,'0')}`,joined:now(),lastLogin:'尚未登录',tasks:0,available:state.gift,frozen:0,consumed:0,deleted:false};state.users.push(added);audit('用户维护',added.id,`新增账号 ${account} · ${reason}`);state.ledger.unshift({id:`A-L-${++state.ledgerSeq}`,at:now(),userId:added.id,account,kind:'注册赠送',amount:state.gift,before:0,after:state.gift,reason:'新增演示账号，一次性赠送',operator:'系统演示'});state.userQuery='';state.userStatus='全部';}
      toast('用户资料已更新，仅在后台本地演示中生效。');
    });
    else if(a==='user-delete'&&u) modal('删除用户 · 演示确认',`<p>将从用户列表移除 ${safe(u.account)}（${u.id}）。关联任务、积分和审计记录保留，不物理删除。</p>${field('删除原因','reason','','text','required')}<div class="notice warn">此操作仅演示软删除。生产数据生命周期待 D-09 确认。</div>`,data=>{if(!data.reason.trim())return '请填写删除原因。';u.deleted=true;state.selectedUser=null;audit('用户维护',u.id,`删除演示用户 · ${data.reason.trim()}`);toast('已移出演示用户列表，诊断与审计记录保留。');},'确认删除');
    else if(a==='user-reset'&&u) modal('重置密码 · 演示',`<p>账号：${safe(u.account)} · ${u.id}</p>${field('新密码 · 演示至少 8 位','password','','password','required minlength="8" autocomplete="new-password"')}${field('确认新密码','confirmPassword','','password','required minlength="8" autocomplete="new-password"')}${field('重置原因','reason','','text','required')}<div class="notice warn">仅记录重置时间与审计原因，不保存密码或哈希，不改变真实登录。生产恢复方案待 D-07 确认。</div>`,data=>{if(data.password!==data.confirmPassword)return '两次新密码不一致，请重新确认。';if(!data.reason.trim())return '请填写重置原因。';u.resetAt=now();audit('密码重置',u.id,`演示重置已确认 · ${data.reason.trim()}`);toast('密码重置演示完成；仅保存时间与审计原因。');},'确认重置演示');
    else if(a==='gift-edit') modal('配置注册赠送',field('赠送积分 · 演示','gift',state.gift,'number','min="0" step="1" required')+'<p>仅影响后续新增的演示账号，不追溯修改已有余额。生产值待确认。</p>',data=>{const amount=Number(data.gift);if(!Number.isSafeInteger(amount)||amount<0)return '赠送积分须为不小于 0 的整数。';const old=state.gift;state.gift=amount;audit('配置修改','注册赠送',old+' → '+amount+' 积分 · 演示');toast('注册赠送配置已保存。');},'保存配置');
    else if(a==='grant-open') modal('发放积分', '<p>选择接收账号，填写数量与原因后确认。仅更新后台演示余额。</p><div class="field"><label for="manage-grantUser">接收用户</label><select id="manage-grantUser" name="userId" required>'+activeUsers().map(u=>'<option value="'+u.id+'">'+safe(u.account)+' · 当前可用 '+u.available+' 积分</option>').join('')+'</select></div>'+field('发放数量','amount','50','number','min="1" step="1" required')+field('发放原因','reason','','text','required'),data=>{const u=user(data.userId),amount=Number(data.amount),reason=data.reason.trim();if(!u||u.deleted)return '请选择有效用户。';if(!Number.isSafeInteger(amount)||amount<1)return '积分须为大于 0 的整数。';if(!reason)return '请填写发放原因。';const before=u.available;u.available+=amount;state.ledger.unshift({id:'A-L-'+(++state.ledgerSeq),at:now(),userId:u.id,account:u.account,kind:'管理员发放',amount,before,after:u.available,reason,operator:'admin-demo'});audit('积分发放',u.id,'+'+amount+' 积分 · '+reason);toast('积分已发放，流水与审计已更新。');},'确认发放积分');
    else if(a==='site-edit') modal('编辑产品介绍','<div class="field"><label for="manage-intro">介绍文案</label><textarea id="manage-intro" name="intro" required maxlength="600">'+safe(state.intro)+'</textarea></div><p>保存后更新当前预览，公开文案仍待确认。</p>',data=>{if(!data.intro.trim())return '请填写产品介绍。';state.intro=data.intro.trim();audit('配置修改','官网介绍','更新介绍预览');toast('产品介绍已保存。');},'保存介绍');
    else if(a==='credit-clear'){state.creditQuery='';render();}
    else if(a==='log-clear'){state.logQuery='';state.logType='全部';render();}
    else if(a==='access') modal('申请独立内容授权',`<p>任务 ${safe(id)}。申请仅记录范围与原因，不自动授予私有内容访问权限。</p>${field('访问原因','reason','','text','required')}`,data=>{if(!data.reason.trim())return '请填写访问原因。';audit('授权申请',id,data.reason.trim());toast('演示申请已记录，私有内容仍隐藏。');},'登记申请');
    else if(a==='agent-edit') {const agent=state.agents.find(x=>x.id===id);modal(`配置 ${agent.name}`,`${field('服务地址 · 演示','endpoint',agent.endpoint,'url','required')}${field('接入版本','version',agent.version,'text','required')}${select('服务状态','status',['模拟启用','停用'],agent.status)}<div class="notice">凭据：已脱敏；完整结果、幂等与回调能力待联调确认。</div>${field('变更原因','reason','','text','required')}`,data=>{if(!data.version.trim()||!data.reason.trim())return '请填写接入版本与变更原因。';Object.assign(agent,{endpoint:data.endpoint.trim(),version:data.version.trim(),status:data.status});audit('配置修改',id,`更新服务配置 · ${data.reason.trim()}`);toast('Agent 演示配置已保存。');});}
    else if(a==='spec-edit') {const spec=state.specs.find(x=>x.id===id);modal('编辑规格与价格 · 演示',`${field('规格名称','name',spec.name,'text','required')}${field('参数与默认组合 · 演示','params',spec.params,'text','required')}${field('积分价格','price',spec.price,'number','required min="1" step="1"')}${select('状态','status',['模拟启用','停用'],spec.status)}${field('发布原因','reason','','text','required')}<div class="notice">保存会发布新模拟版本；已受理任务保留原费用与输入快照。</div>`,data=>{if(!data.name.trim()||!data.params.trim()||!data.reason.trim())return '请填写规格、参数与发布原因。';if(!Number.isSafeInteger(Number(data.price))||Number(data.price)<1)return '积分价格须为大于 0 的整数。';const old=spec.price;Object.assign(spec,{name:data.name.trim(),params:data.params.trim(),price:Number(data.price),status:data.status,version:spec.version+1});audit('配置修改',id,`价格 ${old} → ${spec.price}；demo-p${spec.version} · ${data.reason.trim()}`);toast('新模拟规格与价格版本已发布。');},'发布模拟新版本');}
    return true;
  }
  function bind() {
    document.querySelectorAll('[data-manage-form]').forEach(form=>{
      const formError=form.querySelector('[data-form-error]');
      if(formError){formError.id=`manage-error-${form.dataset.manageForm}`;form.setAttribute('aria-describedby',formError.id);}
      form.onsubmit=e=>{
      e.preventDefault();const data=Object.fromEntries(new FormData(form)),type=form.dataset.manageForm,error=form.querySelector('[data-form-error]');
      const fail=text=>{if(error)error.textContent=text;};
      if(type==='tasks'){state.taskQuery=data.taskQuery.trim();state.taskStatus=data.taskStatus;state.taskAgent=data.taskAgent;}
      if(type==='users'){state.userQuery=data.userQuery.trim();state.userStatus=data.userStatus;}
      if(type==='credits')state.creditQuery=data.creditQuery.trim();
      if(type==='logs'){state.logQuery=data.logQuery.trim();state.logType=data.logType;}
      if(type==='gift'){const amount=Number(data.gift);if(!Number.isSafeInteger(amount)||amount<0)return fail('赠送积分须为不小于 0 的整数。');const old=state.gift;state.gift=amount;audit('配置修改','注册赠送',`${old} → ${amount} 积分 · 测试配置`);toast('注册赠送演示配置已保存。');}
      if(type==='site'){if(!data.intro.trim())return fail('请填写产品介绍。');state.intro=data.intro.trim();audit('配置修改','官网介绍','更新后台介绍预览');toast('产品介绍演示已保存。');}
      if(type==='grant'){
        const u=user(data.userId),amount=Number(data.amount),reason=data.reason.trim();
        if(!u||u.deleted)return fail('请选择有效接收用户。');if(!Number.isSafeInteger(amount)||amount<1)return fail('积分数量须为大于 0 的整数。');if(!reason)return fail('请填写发放原因。');
        modal('确认发放积分 · 演示',`<p>接收账号：${safe(u.account)} / ${u.id}<br>数量：${amount} 积分<br>原因：${safe(reason)}<br>操作人：admin-demo</p><div class="notice">仅增加后台演示账户余额，不改变个人工作台账户，非支付收入。</div>`,()=>{if(u.deleted)return '用户已删除，未发放。';const before=u.available;u.available+=amount;state.ledger.unshift({id:`A-L-${++state.ledgerSeq}`,at:now(),userId:u.id,account:u.account,kind:'管理员发放',amount,before,after:u.available,reason,operator:'admin-demo'});audit('积分发放',u.id,`+${amount} 积分 · ${reason}`);toast('演示积分已发放，后台流水与审计记录已更新。');},'确认发放');return;
      }
      render();
      };
    });
  }
  return {state,content,handle,bind};
})();
