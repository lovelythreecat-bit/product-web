/* Standalone review prototype. No backend, AI, billing or account calls. */
const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const icons = {
  plus:'M12 5v14M5 12h14', arrow:'m9 5 7 7-7 7M4 12h12', back:'m14 5-7 7 7 7', check:'m5 12 4 4L19 6',
  spark:'m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6Z',
  layers:'m12 3 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 16l9 5 9-5',
  file:'M6 3h8l4 4v14H6V3Zm8 0v5h4M9 12h6M9 16h6',
  image:'M3 3h18v18H3V3Zm0 13 5-5 5 5 3-4 5 7M8 7h.01',
  save:'M4 3h14l3 3v15H3V3h1Zm3 0v6h10V3M7 21v-8h10v8',
  upload:'M12 16V3m-5 5 5-5 5 5M4 14v7h16v-7',
  close:'m6 6 12 12M6 18 18 6', edit:'m15 4 5 5-11 11-6 1 1-6L15 4Zm-8 9 4 4',
  copy:'M8 8h13v13H8V8ZM3 16V3h13', refresh:'M20 10a8 8 0 1 0-1 8M20 4v6h-6',
  download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5', video:'M3 5h18v14H3V5Zm6 4 6 3-6 3V9Z',
  long:'M7 2h10v20H7V2Zm0 7h10M7 15h10', eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Zm10-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z',
  clock:'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm0 3v5l4 2', play:'m8 5 11 7-11 7V5Z'
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${icons[name] || icons.file}"/></svg>`;
const button = (label, action, style = '', disabled = false, ico = '') => `<button class="button ${style}" data-action="${action}" ${disabled?'disabled':''}>${ico?icon(ico):''}${label}</button>`;
const originalCopy = '把自己的节奏，戴在耳边\n\n黑色头戴式耳机，以简洁的外观融入日常穿搭。头戴设计搭配包耳式耳罩，通勤路上、办公桌前，或是一个人的休闲时光，都可以为自己留一段听音乐的时间。\n\n· 黑色外观，日常容易搭配\n· 头戴结构，包耳式耳罩\n· 适合通勤、办公与日常休闲\n\n从喜欢的一首歌开始，找到今天的节奏。';
const defaults = {name:'黑色头戴式耳机',product_type:'digital',category:'头戴式耳机',brand:'',origin:'',description:'黑色外观，头戴式结构，包耳式耳罩。',audience:'日常通勤与音乐爱好者',scene:'通勤、办公、日常休闲'};
let saved; try{saved=JSON.parse(localStorage.getItem('yingzuo-quick-design-v1'));}catch{}
let state = {product:{...defaults},materials:2,uploaded:[],copy:originalCopy,selected:[],platform:'',requirements:'以商品为主体，保持黑色外观和头戴式结构；画面简洁，不添加未提供的功能或优惠。',frame:'',copySettings:{copy_type:'宣传文案',platform:'',audience:'日常通勤与音乐爱好者',tone:'自然',max_chars:'',extra_instructions:''},videoRequirements:'围绕耳机外观与日常使用场景展示，节奏自然。',imageReady:false,planReady:false,videoReady:false,failed:false,busy:false,...saved};
let stage = location.hash.slice(1) || 'product', returnFocus = null, pending = null, busyTimer, toastTimer;
const stepNames=['商品确认','营销文案','图片生成','视频生成'];
const prices={copy:10,main:20,detail:20,long:20,video:60}; // Review fixture only.
const types={main:['商品主图',1,'image'],detail:['详情图',3,'layers'],long:['商品长图',1,'long']};
const contract=window.quickGenerationFields;
const {productNames,productKinds,kindFields}=contract;
function allowedProduct(p){const keys=(contract.productGroups[p.product_type]||contract.productGroups.other).flatMap(g=>g.fields);return Object.fromEntries(Object.entries(p).filter(([k])=>keys.includes(k)));}
state.product=allowedProduct(state.product);
if(state.frame==='generated')state.frame='';
function persist(){try{localStorage.setItem('yingzuo-quick-design-v1',JSON.stringify({...state,busy:false,failed:false}));}catch{}}
function notify(t){clearTimeout(toastTimer);$('#toast').textContent=t;$('#toast').hidden=false;toastTimer=setTimeout(()=>$('#toast').hidden=true,3500);}
function goto(s){stage=s;if(location.hash!=='#'+s)location.hash=s;else render();}
function chosenCount(){return state.selected.reduce((n,k)=>n+types[k][1],0);}
function imageCost(){return state.selected.reduce((n,k)=>n+prices[k],0);}
function stepIndex(){return {product:0,copy:1,images:2,results:2,video:3,complete:3}[stage]??0;}
function stamp(){document.querySelectorAll('[data-icon]').forEach(e=>e.innerHTML=icon(e.dataset.icon));}
function photo(cls=''){return `<div class="photo ${cls}" role="img" aria-label="耳机商品设计示例"></div>`;}
function intro(title,note,status=''){return `<div class="intro"><div><h2>${title}</h2><p>${note}</p></div>${status?`<span class="status">${icon('check')}${status}</span>`:''}</div>`;}
function context(){
  const idx=stepIndex();
  $('#context').innerHTML=`<div class="product-mini">${photo()}<div><strong>${esc(state.product.name||'待填写商品')}</strong><small>本次快速生成</small></div></div><h3>创作进度</h3><ul class="rail-list">${stepNames.map((name,i)=>`<li>${icon(i<idx?'check':i===idx?'clock':'file')}<div><strong>${name}</strong><small>${i<idx?'已确认':i===idx?'当前步骤':'等待上一阶段确认'}</small></div></li>`).join('')}</ul><div class="context-section"><h3>${idx===0?'资料只需准备一次':'已确认的内容'}</h3>${idx===0?'<p>商品信息和参考图片会用于后续创作。请保留真实的材质、功能及使用条件。</p>':`<div class="summary-row"><span>商品资料</span><b>已确认</b></div>${idx>1?'<div class="summary-row"><span>营销文案</span><b>已确认</b></div>':''}${idx>2?`<div class="summary-row"><span>图片成果</span><b>${chosenCount()} 张已确认</b></div>`:''}`} </div><div class="context-section"><h3>${stage==='images'?'本次图片清单':'生成与费用'}</h3>${stage==='images'?`<dl>${state.selected.map(k=>`<dt>${types[k][0]} × ${types[k][1]}</dt><dd>${prices[k]} 积分</dd>`).join('')||'<dt>尚未选择</dt><dd>—</dd>'}<dt>合计</dt><dd class="orange">${imageCost()} 积分</dd></dl>`:'<p>每个阶段确认后再继续。生成前确认本次费用，完整成果保存后消费积分。</p>'}<span class="notice-badge">示例报价，以实际配置为准</span></div>`;
}
function footer(note,small,actions){$('#footer').innerHTML=`<div class="footer-note"><span>${note}</span>${small?`<small>${small}</small>`:''}</div><div class="footer-actions">${actions}</div>`;}
function productView(){
 const p=state.product,kind=productKinds.find(k=>k[0]===p.product_type)?.[1]||'待选择';
 const entries=Object.entries(allowedProduct(p)).filter(([k,v])=>!['name','product_type','category'].includes(k)&&v);
 $('#content').innerHTML=intro('先确认这次创作的商品','填写商品属性、上传参考图片，后续内容围绕同一件商品生成。')+
 '<div class="section-title"><h3>商品资料</h3>'+button(p.name?'编辑资料':'填写资料','edit-product','text',false,'edit')+'</div><div class="product-card">'+photo()+'<div><h3>'+esc(p.name||'尚未填写商品名称')+'</h3><p>'+esc(p.category||'尚未填写商品品类')+'</p><dl><dt>商品类型</dt><dd>'+kind+'</dd></dl></div></div><div class="section-title"><h3>已填写资料</h3></div><dl class="facts">'+entries.map(([k,v])=>'<dt>'+productNames[k]+'</dt><dd>'+esc(v)+'</dd>').join('')+'</dl><div class="section-title"><h3>商品参考图片 <small>'+state.materials+' 张</small></h3></div><div class="materials">'+Array.from({length:state.materials},(_,i)=>'<div class="material">'+(state.uploaded[i]?'<img src="'+state.uploaded[i]+'" alt="本地选择的商品图" style="width:88px;height:80px;object-fit:contain">':photo())+'<button data-action="remove-'+i+'" aria-label="移除商品参考图 '+(i+1)+'">'+icon('close')+'</button><small>商品参考图 '+(i+1)+'</small></div>').join('')+'<button class="upload-box" data-action="upload">'+icon('plus')+'上传图片</button></div><div class="section-title"><h3>文案创作要求</h3>'+button('调整要求','copy-settings','text')+'</div><p class="note" style="margin-top:0">'+esc(state.copySettings.copy_type)+' · '+esc(state.copySettings.tone)+(state.copySettings.platform?' · '+esc(state.copySettings.platform):'')+' · '+esc(state.copySettings.audience)+'</p>';
 footer('下一步：生成营销文案 <strong>10</strong> 积分','生成前确认费用',button('确认商品，生成文案','generate-copy','primary',!p.name||!p.product_type,'arrow'));
}
function copyView(){
  $('#content').innerHTML=intro('文案合适，再开始出图','可直接修改下面的文案，确认后的内容将用于图片创作。','文案已生成')+`<div class="copy-backdrop"><div class="copy-paper"><div class="editor-label"><span>营销文案</span><span>${icon('edit')} 可编辑</span></div><textarea class="copy-editor" aria-label="营销文案">${esc(state.copy)}</textarea><div class="editor-bottom"><small>修改将在确认后用于下一阶段</small>${button('复制文案','copy-text','text',false,'copy')}</div></div></div><div class="copy-toolbar">${button('重新生成','regenerate-copy','',false,'refresh')}${button('调整创作要求','copy-settings','quiet')}</div>`;
  footer('确认文案后，选择要生成的图片','本次确认不收费',button('上一步','back-product','quiet',false,'back')+button('确认文案，选择图片','confirm-copy','primary',!state.copy.trim(),'arrow'));
}
const platformOptions=()=>contract.platforms.map(([k,l])=>'<option value="'+k+'" '+(state.platform===k?'selected':'')+'>'+l+'</option>').join('');
function imagesView(){
  $('#content').innerHTML=intro('这次，你想生成哪些图片？','按需选择，可只生成一种；详情图固定为完整的 3 张。')+`<div class="select-head"><label for="platform">目标平台 <small>必选</small></label><select class="control" id="platform"><option value="" disabled ${!state.platform?'selected':''}>请选择目标平台</option>${platformOptions()}</select></div><div class="output-list">${Object.entries(types).map(([k,[label,count,ico]])=>`<label class="output-option"><input type="checkbox" name="output" value="${k}" ${state.selected.includes(k)?'checked':''}><span class="output-icon">${icon(ico)}</span><div><strong>${label}</strong><p>${{main:'突出商品主体，用于商品首屏展示。',detail:'呈现商品外观、结构与使用场景。',long:'将商品信息串联成一张完整长图。'}[k]}</p></div><div class="count"><b>${count} 张</b><small>${prices[k]} 积分 / 次</small></div></label>`).join('')}</div><div class="requirements"><label for="requirements">创作指令 <small>可选</small></label><textarea id="requirements" class="control">${esc(state.requirements)}</textarea></div><p class="note">${icon('file')} 使用已确认的商品资料、参考图片与营销文案。</p>`;
  imagesFooter();
}
function imagesFooter(){const missing=!state.product.category?'请返回商品资料补充商品品类':!state.materials?'请返回商品资料上传商品图片':!state.platform?'请选择目标平台':!state.selected.length?'请至少选择一种图片':'';footer(`已选 ${state.selected.length} 类 · ${chosenCount()} 张 <strong>${imageCost()}</strong> 积分`,missing||'详情图 3 张按一次图片任务计费（示例）',button('上一步','back-copy','quiet',false,'back')+button('确认费用并生成图片','generate-images','primary',!!missing,'arrow'));}
function resultArt(type,index=0){
  if(type==='long')return `<div class="result-art long">${['从外观开始，认识它','让日常，多一点自己的节奏'].map((t,i)=>`<div class="long-segment">${photo()}<span><strong>${t}</strong><br>${i?'通勤 / 办公 / 休闲':'黑色 · 头戴式 · 包耳结构'}</span></div>`).join('')}</div>`;
  return `<div class="result-art ${type==='detail'?'detail':''}">${photo()}<b>${type==='main'?'让日常，多一点<br>自己的节奏':['黑色，简单好搭','看得见的头戴结构','留一段自己的时间'][index]}</b><small>${type==='main'?'黑色头戴式耳机':['简洁外观 · 日常搭配','包耳式耳罩','通勤 / 办公 / 日常休闲'][index]}</small></div>`;
}
function resultsView(){
  const list=state.selected.flatMap(k=>Array.from({length:types[k][1]},(_,i)=>[k,i]));
  $('#content').innerHTML=intro('图片已就绪，确认后继续','打开预览查看完整图片，确认这一组成果后再生成视频。',`${chosenCount()} 张已生成`)+`<div class="gallery-head"><h3>本次图片成果</h3><small>${state.selected.length} 类 · ${chosenCount()} 张</small></div><div class="image-grid">${list.map(([k,i])=>`<div class="result-tile">${resultArt(k,i)}<div class="result-caption"><span>${types[k][0]}${k==='detail'?' '+(i+1):''}</span><button data-action="preview-${k}-${i}">预览${k==='long'?'长图':''}</button></div></div>`).join('')}</div><div class="copy-toolbar">${button('重新选择图片内容','reselect-images','quiet',false,'back')}${button('重新生成此组','regenerate-images','quiet',false,'refresh')}</div><p class="note">图片中有不满意的内容，可重新生成此组；原成果保留，重新确认费用。</p>`;
  footer(`已生成 ${chosenCount()} 张图片`,'确认后进入视频设置',button('保存并退出','exit','quiet')+button('确认图片，继续视频','confirm-images','primary',false,'arrow'));
}
const planFixture={plan_version:1,document:{creative:'以商品整体外观开场，展示头戴结构和包耳式耳罩，最后以完整商品画面收束。',audience:'日常通勤与音乐爱好者',selling_points:['黑色外观','头戴式结构','包耳式耳罩'],duration_seconds:15,aspect_ratio:'9:16',subtitles:true,voiceover:false,music:false,shared_visual:{product_reference:'保持参考图中的商品外观',scene:'简洁的日常环境',lighting:'柔和自然光',palette:'暖色背景与黑色商品',style:'简洁商品展示'},shots:[{content:'展示完整商品外观',action:'商品保持静止',shot_size:'全景',camera:'缓慢推进'},{content:'展示头戴结构与包耳式耳罩',action:'平稳展示商品细节',shot_size:'近景',camera:'缓慢平移'}]}};
function videoView(){
 const d=planFixture.document;
 $('#content').innerHTML=intro(state.planReady?'视频方案已准备好':'把满意的图片，接着做成视频',state.planReady?'查看并确认方案后继续生成，本次确认不会再次收费。':'从已上传商品图片中选择本次视频的首帧。')+(state.planReady?
 '<div class="plan" style="margin-top:0"><h3>视频创作方案</h3><dl><dt>创意方向</dt><dd>'+esc(d.creative)+'</dd><dt>目标人群</dt><dd>'+esc(d.audience)+'</dd><dt>视频时长</dt><dd>'+d.duration_seconds+' 秒</dd><dt>画面比例</dt><dd>'+d.aspect_ratio+'</dd></dl></div><p class="note">此处为返回方案的只读示例，不提供新的时长、比例或声音设置。</p>':
 '<div class="section-title" style="margin-top:0"><h3>视频首帧 <small>必选</small></h3></div><div class="frame-grid">'+Array.from({length:state.materials},(_,i)=>['reference-'+(i+1),'商品参考图 '+(i+1)]).map(([id,label])=>'<label class="frame-option"><input type="radio" name="frame" value="'+id+'" '+(state.frame===id?'checked':'')+'>'+photo()+'<span>'+label+'</span></label>').join('')+'</div><div class="requirements"><label for="video-requirements">创作指令 <small>可选</small></label><textarea id="video-requirements" class="control">'+esc(state.videoRequirements)+'</textarea></div><p class="note">先确认费用并生成方案，再查看并确认方案出片。无需重复填写商品资料。</p>');
 videoFooter();
}
function videoFooter(){footer(state.planReady?'本次视频 60 积分 · 已冻结':'本次视频 <strong>60</strong> 积分',state.planReady?'方案确认不重复收费':'先生成方案，确认后出片',button('返回图片','back-results','quiet',false,'back')+button(state.planReady?'查看并确认方案':'确认费用，生成视频方案',state.planReady?'view-plan':'plan-video','primary',!state.frame,'arrow'));}

function completeView(){
  $('#content').innerHTML=intro('这次创作，全部完成','文案、图片与视频集中保留，随时回来看。','已完成')+`<div class="video-stage">${photo()}<button data-action="play-video" aria-label="查看视频演示说明">${icon('play')}</button><span>视频预览 · 设计占位</span></div><div class="completion-list"><div class="completion-item">${icon('check')} 营销文案 · 1 份</div><div class="completion-item">${icon('check')} 图片 · ${chosenCount()} 张</div><div class="completion-item">${icon('check')} 视频 · 1 条</div></div><div class="copy-toolbar">${button('查看文案','open-copy','',false,'file')}${button('查看图片','back-results','',false,'image')}${button('下载成果','download','',false,'download')}</div>`;
  footer('全部成果已汇总','可从最近任务继续查看',button('返回工作台','entry','quiet')+button('完成并查看作品','finish','primary',false,'arrow'));
}
function entryView(){
  $('.mode-tag').hidden=true;$('.page-top>.button').hidden=true;
  $('.wizard').hidden=true;
  const el=document.createElement('div');el.className='entry-placeholder';el.innerHTML=`<section class="entry-canvas"><div>${icon('spark')}<h2>从一个商品，开始一整套创作</h2><p>按步骤确认，依次生成文案、图片与视频。</p><a href="#product" class="button primary">${icon('spark')}快速生成${icon('arrow')}</a><p class="note">也可以在右侧单独创作文案、图片或视频。</p></div></section><aside class="entry-panel"><div class="tabs"><span>文案</span><span>图片</span><span>视频</span></div><div class="empty-product"><div class="section-title" style="margin:0"><h3>商品资料</h3>${button('填写资料','edit-product','text')}</div><p>添加商品资料，让创作更贴合商品。</p></div><div class="section-title"><h3>创作指令</h3></div><textarea class="control" placeholder="描述这次希望生成的内容" aria-label="创作指令"></textarea>${button('确认费用并生成','single-generation','primary')}</aside>`;$('#main').append(el);
}
function render(){
  $('.entry-placeholder')?.remove();$('.wizard').hidden=false;$('.mode-tag').hidden=false;$('.page-top>.button').hidden=false;
  $('#stepper').innerHTML=stepNames.map((n,i)=>`<li class="${i<stepIndex()?'done':i===stepIndex()?'current':''}" ${i===stepIndex()?'aria-current="step"':''}><span class="bubble">${i<stepIndex()?icon('check'):i+1}</span><div><strong>${n}</strong><small>${['资料与参考图片','生成、编辑并确认','选择内容并生成','首帧与视频方案'][i]}</small></div></li>`).join('');
  if(stage==='entry')entryView();else if(state.busy)renderBusy();else if(state.failed)renderFailure();else ({product:productView,copy:copyView,images:imagesView,results:resultsView,video:videoView,complete:completeView}[stage]||productView)();
  context();stamp();
}
function openDialog(title,body,actions,drawer=false){returnFocus=document.activeElement;const d=$('#overlay');d.classList.toggle('drawer',drawer);$('#overlay-content').innerHTML=`<div class="overlay-header"><h2 id="overlay-title">${title}</h2><button data-action="close" aria-label="关闭">${icon('close')}</button></div><div class="overlay-body">${body}</div><div class="overlay-actions">${actions}</div>`;d.showModal();const cancel=d.querySelector('[data-action="close"]:last-child');(cancel||d.querySelector('button'))?.focus();}
function closeDialog(){$('#overlay').close();returnFocus?.isConnected&&returnFocus.focus();}
function productField(k,p){const label=productNames[k],long=contract.longProductFields.includes(k);return '<label class="field '+(long?'wide':'')+'">'+label+(['name','product_type'].includes(k)?' *':'')+(k==='product_type'?'<select name="'+k+'" required>'+productKinds.map(([v,l])=>'<option value="'+v+'" '+(p[k]===v?'selected':'')+'>'+l+'</option>').join('')+'</select>':long?'<textarea name="'+k+'" rows="3" maxlength="600">'+esc(p[k]||'')+'</textarea>':'<input name="'+k+'" value="'+esc(p[k]||'')+'" maxlength="120" '+(k==='name'?'required':'')+' placeholder="填写实际'+label+'">')+'</label>';}
function productDrawer(p=state.product){
 const groups=contract.productGroups[p.product_type]||contract.productGroups.other;
 openDialog('编辑商品资料','<form id="product-form"><p>选择商品类型后填写对应规格。仅填写真实信息，未知规格留空。</p>'+groups.map(({title,fields})=>'<h3>'+title+'</h3><div class="inline-form">'+fields.map(k=>productField(k,p)).join('')+'</div>').join('')+'</form>',button('取消','close')+'<button class="button primary" type="submit" form="product-form">保存商品资料</button>',true);
}
function copySettings(){openDialog('文案创作要求','<form id="copy-settings-form"><div class="inline-form">'+contract.textFields.map(([k,l])=>'<label class="field '+(['extra_instructions','max_chars'].includes(k)?'wide':'')+'">'+l+(k==='extra_instructions'?'<textarea name="'+k+'" rows="3">'+esc(state.copySettings[k])+'</textarea>':'<input name="'+k+'" value="'+esc(state.copySettings[k])+'" '+(k==='max_chars'?'type="number" min="1" step="1" placeholder="留空表示不限制"':'')+(contract.textSuggestions[k]?' list="suggestion-'+k+'"':'')+'>'+(contract.textSuggestions[k]?'<datalist id="suggestion-'+k+'">'+contract.textSuggestions[k].map(v=>'<option value="'+esc(v)+'">').join('')+'</datalist>':''))+'</label>').join('')+'<label class="field wide">创作指令<textarea name="instruction" rows="4">'+esc(state.copyInstruction||'')+'</textarea></label></div></form>',button('取消','close')+'<button class="button primary" type="submit" form="copy-settings-form">保存要求</button>',true);}

function charge(kind,callback){
  pending=callback;let rows=kind==='images'?state.selected.map(k=>[types[k][0]+' × '+types[k][1],prices[k]]):[[kind==='copy'?'营销文案 × 1':'视频 × 1',prices[kind]]];let total=rows.reduce((n,r)=>n+r[1],0);
  openDialog('确认本次生成费用',`<p>商品：${esc(state.product.name)}</p><dl class="charge-list">${rows.map(([l,v])=>`<dt>${l}</dt><dd>${v} 积分</dd>`).join('')}</dl><div class="charge-total"><span>本次合计</span><span><strong>${total}</strong> 积分</span></div><p class="note">提交后冻结，完整成果保存后消费。失败后可重试或主动释放积分。此处为示例报价。</p>${kind==='images'?'<p class="note">所选类型分别建立任务。详情图 3 张作为一次完整交付；部分失败时保留已成功成果。</p>':''}`,button('取消','close')+button('确认费用并生成','accept-charge','primary'));
}
function start(kind,next){state.failed=false;state.busy=kind;render();busyTimer=setTimeout(()=>{state.busy=false;if(kind==='copy'){state.copy=originalCopy;state.imageReady=false;state.planReady=false;state.videoReady=false;}if(kind==='images')state.imageReady=true;if(kind==='plan')state.planReady=true;if(kind==='video')state.videoReady=true;persist();goto(next);},950);}
function renderBusy(){const title={copy:'正在生成营销文案',images:'正在生成所选图片',plan:'正在准备视频方案',video:'正在生成视频'}[state.busy];$('#content').innerHTML=`<div class="progress-state">${icon('spark')}<h2>${title}</h2><p>正在使用已确认的商品资料与创作要求。</p><div class="progress-line"></div><small>完成后停留在当前阶段，等你确认再继续。</small></div>`;footer('生成中','关闭页面不会取消已受理任务',button('生成中…','noop','primary',true));}
function renderFailure(){
 $('#content').innerHTML=intro('部分图片需要处理','成功成果保留；失败任务的积分结算沿用现有规则。')+'<div class="image-grid"><div>'+resultArt('main')+'<div class="result-caption"><span>商品主图</span><span>已保存</span></div></div></div><div class="error-panel"><strong>详情图（3 张）生成失败</strong><p>'+(state.failedReleased?'对应 20 积分已释放，不能再使用原冻结额度重试。':'生成失败，积分保持冻结。你可以重试，或释放积分返还可用余额。')+'</p>'+button(state.failedReleased?'重新生成失败项':'重试','retry-failed')+(!state.failedReleased?button('释放积分','release-failed','quiet'):'')+'</div><p class="note">状态不明时先核查原任务；保存异常先恢复原成果。</p>';
 footer('请先完成失败的图片任务','已成功成果不会重复生成',button('重新选择','reselect-images','quiet')+button('确认图片，继续视频','confirm-images','primary',true));
}
function preview(k,i){let art=resultArt(k,i);if(k==='long')art=`<div class="result-art long">${['黑色头戴式耳机','外观，简洁耐看','头戴式结构','包耳式耳罩','日常使用场景','找到自己的节奏'].map(t=>`<div class="long-segment">${photo()}<span><strong>${t}</strong><br>商品长图 · 排版示例</span></div>`).join('')}</div>`;openDialog(types[k][0]+(k==='long'?' · 完整长图':''),`<div class="preview-art ${k==='long'?'long-preview':''}">${art}</div>`,button('关闭','close'));}
function viewPlan(){
 const d=planFixture.document,visual={product_reference:'商品参考',scene:'场景',lighting:'光线',palette:'配色',style:'风格',character:'人物',scene_change:'场景衔接'},shotLabels={content:'画面',action:'动作',shot_size:'景别',camera:'运镜',start_frame:'起始帧',end_frame:'结束帧',subtitle_text:'字幕',voiceover_text:'旁白'};
 const rows=[['创意方向',d.creative],['目标人群',d.audience],['商品卖点',d.selling_points.join('、')],['视频时长',d.duration_seconds+' 秒'],['画面比例',d.aspect_ratio],['字幕',d.subtitles?'开启':'关闭'],['旁白',d.voiceover?'开启':'关闭'],['音乐',d.music?'开启':'关闭'],...Object.entries(visual).filter(([k])=>d.shared_visual[k]).map(([k,l])=>[l,d.shared_visual[k]])];
 openDialog('视频创作方案','<p>方案版本 '+planFixture.plan_version+'</p><dl class="facts">'+rows.map(([l,v])=>'<dt>'+l+'</dt><dd>'+esc(v)+'</dd>').join('')+'</dl>'+d.shots.map((shot,i)=>'<h3>镜头 '+(i+1)+'</h3><dl class="facts">'+Object.entries(shotLabels).filter(([k])=>shot[k]!==undefined).map(([k,l])=>'<dt>'+l+'</dt><dd>'+esc(shot[k])+'</dd>').join('')+'</dl>').join(''),button('关闭','close')+button('确认此方案','render-video','primary'),true);
}

document.addEventListener('click',e=>{
  const n=e.target.closest('[data-action],[data-notice]');if(!n)return;if(n.dataset.notice){notify(n.dataset.notice);return;}const a=n.dataset.action;
  if(a==='close'){closeDialog();return;}if(a==='entry'){persist();goto('entry');return;}if(a==='exit'){persist();goto('entry');notify('本地原型草稿已保存，点击快速生成可继续查看。');return;}
  if(a==='edit-product'){productDrawer();return;}if(a==='copy-settings'){copySettings();return;}if(a==='upload'){$('#upload').click();return;}
  if(a.startsWith('remove-')){const i=+a.split('-')[1];state.materials--;state.uploaded.splice(i,1);persist();render();return;}
  if(a==='generate-copy'||a==='regenerate-copy'){charge('copy',()=>start('copy','copy'));return;}
  if(a==='accept-charge'){closeDialog();const fn=pending;pending=null;fn?.();return;}
  if(a==='confirm-copy'){state.imageReady=false;state.planReady=false;persist();goto('images');return;}
  if(a==='back-product'){goto('product');return;}if(a==='back-copy'){goto('copy');return;}if(a==='back-results'){goto('results');return;}
  if(a==='reselect-images'){state.failed=false;goto('images');return;}
  if(a==='generate-images'||a==='regenerate-images'){charge('images',()=>start('images','results'));return;}
  if(a.startsWith('preview-')){const [,k,i]=a.split('-');preview(k,+i);return;}
  if(a==='confirm-images'){persist();goto('video');return;}
  if(a==='plan-video'){charge('video',()=>start('plan','video'));return;}
  if(a==='render-video'){if($('#overlay').open)closeDialog();openDialog('确认视频方案',`<p>将按已查看的方案开始生成视频。使用已冻结的 60 积分，不再次收费。</p>`,button('取消','close')+button('确认方案并出片','accept-plan','primary'));return;}
  if(a==='accept-plan'){closeDialog();start('video','complete');return;}if(a==='view-plan'){viewPlan();return;}
  if(a==='retry-failed'){pending=()=>{state.failedReleased=false;start('images','results');};openDialog(state.failedReleased?'重新生成 · 再次收费':'确认重试',state.failedReleased?'<p>仅重新生成失败项，保留已成功成果。</p><div class="charge-total"><span>本次将冻结</span><strong>20 积分</strong></div>':'<p>使用本任务的原始商品资料和指令重新创作。已冻结的 20 积分将用于本次重试，完整成果保存后消费；原报价失效时不提交。</p>',button('取消','close')+button(state.failedReleased?'确认并冻结积分':'确认重试','accept-charge','primary'));return;}
  if(a==='release-failed'){openDialog('确认释放积分','<p>将本任务冻结的 20 积分返还可用余额。释放后，此任务不能再使用冻结额度重试。</p>',button('取消','close')+button('确认释放积分','accept-release','primary'));return;}
  if(a==='accept-release'){state.failedReleased=true;closeDialog();renderFailure();return;}
  if(a==='copy-text'){navigator.clipboard?.writeText(state.copy).then(()=>notify('文案已复制。')).catch(()=>notify('请选中文案后手动复制。'));return;}
  if(a==='download'){notify('原型只展示下载入口；正式版下载对应的真实成果。');return;}
  if(a==='play-video'){notify('这是视频成果的设计占位，尚未调用视频生成服务。');return;}
  if(a==='finish'){notify('流程已完成。正式版进入“我的作品”，查看这一组成果。');return;}
  if(a==='open-copy'){openDialog('已确认营销文案',`<p style="white-space:pre-wrap;color:var(--ink)">${esc(state.copy)}</p>`,button('关闭','close'));return;}
  if(a==='single-generation'){notify('单独创作入口沿用现有工作台，本轮只评审快速生成。');}
});
document.addEventListener('input',e=>{
  if(e.target.matches('.copy-editor')){state.copy=e.target.value;const next=$('[data-action="confirm-copy"]');if(next)next.disabled=!state.copy.trim();persist();}
  if(e.target.id==='requirements'){state.requirements=e.target.value;persist();}
  if(e.target.id==='video-requirements'){state.videoRequirements=e.target.value;persist();}
});
document.addEventListener('change',e=>{
  if(e.target.name==='output'){state.selected=[...document.querySelectorAll('[name="output"]:checked')].map(x=>x.value);imagesFooter();context();persist();}
  if(e.target.id==='platform'){state.platform=e.target.value;imagesFooter();context();persist();}
  if(e.target.name==='frame'){state.frame=e.target.value;videoView();persist();}
  if(e.target.id==='recent-task'){notify('历史任务入口沿用现有工作台；本原型展示当前快速生成流程。');e.target.selectedIndex=0;}
  if(e.target.name==='product_type'&&e.target.closest('#product-form')){const p=Object.fromEntries(new FormData($('#product-form')));closeDialog();productDrawer(p);}
});
document.addEventListener('submit',e=>{e.preventDefault();if(e.target.id==='product-form'){const values=Object.fromEntries(new FormData(e.target));state.product=allowedProduct(values);state.imageReady=false;state.planReady=false;closeDialog();persist();render();notify('商品资料已保存。');}if(e.target.id==='copy-settings-form'){const values=Object.fromEntries(new FormData(e.target));state.copyInstruction=values.instruction;delete values.instruction;state.copySettings=values;closeDialog();persist();render();}});
$('#overlay').addEventListener('cancel',e=>e.preventDefault());
$('#upload').addEventListener('change',async e=>{for(const f of [...e.target.files]){if(!f.type.startsWith('image/'))continue;const url=await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.readAsDataURL(f);});state.uploaded.push(url);state.materials++;}persist();render();notify('图片已在本地原型中载入。');e.target.value='';});
$('#demo-error').addEventListener('click',()=>{clearTimeout(busyTimer);state.busy=false;state.failed=true;state.failedReleased=false;state.selected=['main','detail'];goto('results');});
window.addEventListener('hashchange',()=>{stage=location.hash.slice(1)||'product';if(['results','video','complete'].includes(stage)&&!state.selected.length)state.selected=['main','detail','long'];render();});
if(['results','video','complete'].includes(stage)&&!state.selected.length)state.selected=['main','detail','long'];
render();
