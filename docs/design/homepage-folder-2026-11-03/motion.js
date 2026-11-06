const reduced = matchMedia('(prefers-reduced-motion: reduce)');
function reflectMotionPreference(){document.documentElement.classList.toggle('reduced-motion',reduced.matches)}
reflectMotionPreference();
reduced.addEventListener('change',reflectMotionPreference);
const panel = document.querySelector('#folder-panel');
const folderTabs = [...document.querySelectorAll('[data-folder]')];
const folderContent = [
  {tag:'图像创作',title:'让好商品，<br>先被看见。',description:'主图、详情、场景图，把商品的每一面都表达清楚。',link:'#images',images:[['phone-campaign.webp','手机商品广告创作','01 / 商品主图'],['beauty-campaign.webp','美妆商品广告创作','02 / 美妆场景'],['audio-campaign.webp','耳机商品广告创作','03 / 数码广告']]},
  {tag:'视频创作',title:'把商品卖点，<br>变成好镜头。',description:'从口播到种草，让内容有画面，也有故事。',link:'#video',images:[['phone-creator.webp','手机口播静态分镜','01 / 口播分镜'],['phone-detail.webp','手机细节静态分镜','02 / 产品特写'],['phone-campaign.webp','手机展示静态分镜','03 / 商品展示']]},
  {tag:'双工作台',title:'新手和老手，<br>都有好方法。',description:'一步步引导，或按自己的节奏创作。',link:'#workspace',images:[['phone-source.webp','用于创作的手机素材','01 / 准备素材'],['phone-campaign.webp','手机场景图','02 / 创作表达'],['phone-detail.webp','手机细节图','03 / 查看成果']]},
  {tag:'玲玲陪练',title:'每一步，<br>都有人陪你走。',description:'选风格、说卖点、理清下一步，不用独自摸索。',link:'#lingling',images:[['01-character-front.png','玲玲 AI 创作陪练','01 / 玲玲陪你'],['phone-source.webp','手机商品素材','02 / 说说商品'],['phone-campaign.webp','手机创作画面','03 / 看见想法']]},
  {tag:'一套素材，多种场景',title:'从商品主图，<br>到带货的每一幕。',description:'让同一件商品，在不同内容里都出彩。',link:'#delivery',images:[['phone-campaign.webp','手机商品广告图','01 / 商品主图'],['phone-detail.webp','手机材质与镜头细节','02 / 细节表达'],['phone-creator.webp','手机口播静态分镜','03 / 视频分镜']]}
];
function selectFolder(index, focus = false) {
  const item = folderContent[index];
  folderTabs.forEach((tab,i)=>{tab.setAttribute('aria-selected',String(i===index));tab.tabIndex=i===index?0:-1;tab.querySelector('.tab-sign').textContent=i===index?'−':'＋'});
  panel.setAttribute('aria-labelledby',folderTabs[index].id);
  panel.querySelector('.folio').textContent=item.tag;
  panel.querySelector('h2').innerHTML=item.title;
  panel.querySelector('.folder-description').textContent=item.description;
  panel.querySelector('.folder-more').href=item.link;
  panel.querySelectorAll('figure').forEach((figure,i)=>{const img=figure.querySelector('img');img.src=`assets/${item.images[i][0]}`;img.alt=item.images[i][1];img.classList.toggle('character',item.images[i][0].startsWith('01-'));figure.querySelector('figcaption').textContent=item.images[i][2]});
  if (focus) folderTabs[index].focus();
  if(window.gsap&&!reduced.matches) gsap.fromTo(panel.children,{y:8,opacity:.4},{y:0,opacity:1,duration:.24,stagger:.035,ease:'power2.out',overwrite:true,clearProps:'transform,opacity'});
}
function tabKeys(event,index,tabs,select) {
  if(event.ctrlKey||event.metaKey||event.altKey)return;
  let next=index;
  if(['ArrowDown','ArrowRight'].includes(event.key)) next=(index+1)%tabs.length;
  else if(['ArrowUp','ArrowLeft'].includes(event.key)) next=(index+tabs.length-1)%tabs.length;
  else if(event.key==='Home') next=0;
  else if(event.key==='End') next=tabs.length-1;
  else return;
  event.preventDefault();select(next,true);
}
folderTabs.forEach((tab,index)=>{tab.addEventListener('click',()=>selectFolder(index));tab.addEventListener('keydown',event=>tabKeys(event,index,folderTabs,selectFolder))});
const modeTabs=[...document.querySelectorAll('[data-mode]')];
const beginner=document.querySelector('#workspace-body').innerHTML;
const pro='<div class="pro-tools"><span>图片创作</span><span>文案</span><span>视频</span></div><div class="pro-editor"><img src="assets/phone-campaign.webp" alt="专业工作台手机创作画面"><aside><b>创作方向</b><span>商品：手机</span><span>场景：通勤</span><span>风格：简洁</span><span>用途：主图</span></aside></div><div class="prompt-preview">为这款手机设计简洁的通勤场景 <span aria-hidden="true">↗</span></div>';
function selectMode(index,focus=false){
  modeTabs.forEach((tab,i)=>{tab.setAttribute('aria-selected',String(i===index));tab.tabIndex=i===index?0:-1});
  document.querySelector('#workspace-preview').setAttribute('aria-labelledby',modeTabs[index].id);
  document.querySelector('#workspace-body').innerHTML=index===0?beginner:pro;
  document.querySelector('#workspace-title').textContent=index===0?'我的第一组商品内容':'我的商品创作';
  document.querySelector('#mode-description').textContent=index===0?'说需求、选风格、看成果，每一步都有清楚的引导。':'整理商品资料与创作方向，按你的节奏推进内容。';
  if(focus)modeTabs[index].focus();
  if(window.gsap&&!reduced.matches)gsap.fromTo('#workspace-body',{opacity:.4,y:8},{opacity:1,y:0,duration:.24,clearProps:'opacity,transform',overwrite:true});
}
modeTabs.forEach((tab,index)=>{tab.addEventListener('click',()=>selectMode(index));tab.addEventListener('keydown',event=>tabKeys(event,index,modeTabs,selectMode))});
if(window.gsap&&window.ScrollTrigger){
  gsap.registerPlugin(ScrollTrigger);
  const media=gsap.matchMedia();
  media.add('(prefers-reduced-motion: no-preference)',()=>{
    gsap.from('.hero-copy > *',{y:15,opacity:0,duration:.35,stagger:.06,ease:'power2.out',clearProps:'transform,opacity'});
    gsap.from('.folders',{y:20,opacity:0,duration:.45,delay:.18,ease:'power2.out',clearProps:'transform,opacity'});
    gsap.utils.toArray('.intro h2,.section-top h2,.chapter-copy h2,.closing h2').forEach(el=>gsap.from(el,{y:18,opacity:0,duration:.5,ease:'power2.out',scrollTrigger:{trigger:el,start:'top 94%',once:true},clearProps:'transform,opacity'}));
    const small=matchMedia('(max-width:520px)').matches;
    const spread=gsap.timeline({scrollTrigger:{trigger:'.spread-stage',start:'top 88%',end:'center 55%',scrub:true}});
    spread.fromTo('.spread.source',{x:small?30:85,rotation:0},{x:0,rotation:-9,ease:'none'},0)
      .fromTo('.spread.detail',{x:small?-30:-85,rotation:0},{x:0,rotation:10,ease:'none'},0)
      .fromTo('.spread.campaign',{scale:.9},{scale:1,ease:'none'},0);
    gsap.from('.flow-list li',{y:16,opacity:0,stagger:.07,duration:.4,scrollTrigger:{trigger:'.flow-list',start:'top 92%',once:true},clearProps:'transform,opacity'});
  });
}
