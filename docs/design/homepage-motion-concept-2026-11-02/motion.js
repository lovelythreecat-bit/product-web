const root=document.documentElement;
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const mobile=matchMedia('(max-width: 760px)');
let paused=reduced.matches;
root.classList.add('js-motion');
const pauseButton=document.querySelector('#motion-toggle');
const story=document.querySelector('.story');
const screen=document.querySelector('.story-screen');
const steps=[...document.querySelectorAll('[data-step]')];
const scenes=[...document.querySelectorAll('.scene')];
const playButton=document.querySelector('#story-play');
let step=0,manualUntil=-1,tour=null,lastY=scrollY;
function setStep(n){step=n;screen.dataset.stage=String(n);steps.forEach((b,i)=>{b.classList.toggle('active',i===n);b.setAttribute('aria-pressed',String(i===n))});scenes.forEach((s,i)=>{s.inert=i!==n;s.setAttribute('aria-hidden',String(i!==n))})}
function stopTour(){if(tour)clearInterval(tour);tour=null;playButton.textContent=paused||reduced.matches?'下一步演示 →':'播放创作演示 ▷';playButton.setAttribute('aria-pressed','false')}
function updatePause(){const stopped=paused||reduced.matches;root.classList.toggle('paused',stopped);pauseButton.disabled=reduced.matches;pauseButton.textContent=reduced.matches?'系统已减少动效':paused?'开启动效':'暂停动效';pauseButton.setAttribute('aria-pressed',String(stopped));if(stopped)stopTour();else if(!tour)playButton.textContent='播放创作演示 ▷';document.dispatchEvent(new Event('motionstatechange'))}
pauseButton.addEventListener('click',()=>{paused=!paused;updatePause();updateScroll()});
reduced.addEventListener('change',()=>{paused=reduced.matches;updatePause();updateScroll()});
steps.forEach(b=>b.addEventListener('click',()=>{stopTour();manualUntil=scrollY;setStep(Number(b.dataset.step))}));
playButton.addEventListener('click',()=>{if(tour){stopTour();return}if(paused||reduced.matches){setStep((step+1)%3);return}setStep(0);manualUntil=scrollY;playButton.textContent='暂停演示 Ⅱ';playButton.setAttribute('aria-pressed','true');let advances=0;tour=setInterval(()=>{if(document.hidden)return;setStep((step+1)%3);advances++;if(advances===5)stopTour()},3500)});
const hero=document.querySelector('.hero');
function updateScroll(){const y=scrollY;const p=Math.min(1,y/500);if(!paused&&!reduced.matches){root.style.setProperty('--hero-rotate',`${8-p*8}deg`);root.style.setProperty('--hero-y',`${-p*20}px`)}if(!mobile.matches&&!reduced.matches&&!paused){const r=story.getBoundingClientRect();const range=story.offsetHeight-innerHeight;const progress=Math.max(0,Math.min(.999,(80-r.top)/Math.max(1,range)));if(manualUntil>=0&&Math.abs(y-manualUntil)>100){manualUntil=-1;stopTour()}if(manualUntil<0&&!tour)setStep(Math.min(2,Math.floor(progress*3)));screen.style.setProperty('--screen-rotate',`${(1-progress)*-7}deg`)}lastY=y}
let scheduled=false;addEventListener('scroll',()=>{if(!scheduled){scheduled=true;requestAnimationFrame(()=>{updateScroll();scheduled=false})}},{passive:true});addEventListener('resize',updateScroll);updatePause();setStep(0);updateScroll();
const reveals=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('seen');reveals.unobserve(e.target)}}),{threshold:.12});document.querySelectorAll('.reveal').forEach(e=>reveals.observe(e));
const visible=new IntersectionObserver(entries=>entries.forEach(e=>e.target.classList.toggle('offscreen',!e.isIntersecting)),{rootMargin:'100px'});document.querySelectorAll('.hero-showcase,.lingling-invite,.story-screen,.reel,.character-stage,.delivery-diagram').forEach(e=>visible.observe(e));
document.addEventListener('visibilitychange',()=>{root.classList.toggle('backgrounded',document.hidden);if(document.hidden)stopTour()});
document.querySelectorAll('.tilt').forEach(card=>{card.addEventListener('pointermove',e=>{if(e.pointerType!=='mouse'||paused||reduced.matches)return;const r=card.getBoundingClientRect();card.style.setProperty('--rx',`${-(e.clientY-r.top-r.height/2)/r.height*7}deg`);card.style.setProperty('--ry',`${(e.clientX-r.left-r.width/2)/r.width*7}deg`)});card.addEventListener('pointerleave',()=>{card.style.setProperty('--rx','0deg');card.style.setProperty('--ry','0deg')})});
const guideCopy=['卡在哪一步，玲玲就在哪一步。','主图、详情、海报，输入即出。','每一步都有人陪你走完，再也不怕「不会用」。','生成即分发。'];
document.querySelectorAll('[data-guide]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-guide]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));document.querySelector('#speech').textContent=guideCopy[Number(b.dataset.guide)]}));
document.querySelectorAll('[data-workspace]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-workspace]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));const pro=b.dataset.workspace==='pro';document.querySelector('#workspace-visual').classList.toggle('is-pro',pro);document.querySelector('#workspace-title').textContent=pro?'想要完全掌控？':'零基础，对话即出片';document.querySelector('#workspace-copy').textContent=pro?'想要完全掌控？专业工作台给你图层、参数、批量与模板。飞马不替你决定，只让你更快。':'专业工作台给老手完整控制权；小白工作台把专业能力收进一句对话——选品类、说卖点、挑风格，智能体替你排兵布阵，零基础也能出品专业级素材。'}));
const themeButton=document.querySelector('#theme-toggle');themeButton.addEventListener('click',()=>{const dark=root.dataset.theme!=='dark';root.dataset.theme=dark?'dark':'light';themeButton.textContent=dark?'浅色':'深色';themeButton.setAttribute('aria-label',dark?'切换浅色主题':'切换深色主题')});
const dialog=document.querySelector('#review-dialog');let opener;
function showDialog(entry,e){opener=e.currentTarget;document.querySelector('#entry-note').hidden=!entry;dialog.showModal();document.querySelector('#dialog-close').focus()}
document.querySelector('#about-open').addEventListener('click',e=>showDialog(false,e));document.querySelectorAll('[data-entry]').forEach(b=>b.addEventListener('click',e=>showDialog(true,e)));document.querySelector('#dialog-close').addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>opener?.focus());

// Content remains ordinary DOM. The gallery only changes presentation.
const showcase=document.querySelector('.hero-showcase');
const gallery=document.querySelector('.orbit-gallery');
const cards=[...document.querySelectorAll('[data-product]')];
const productButtons=[...document.querySelectorAll('[data-select-product]')];
const autoButton=document.querySelector('.gallery-auto');
const cycleBar=document.querySelector('.stage-cycle i');
let productIndex=0,autoStopped=false,heroVisible=true,hovering=false,focusInHero=false,cycleElapsed=0,cycleFrame=0,lastFrame=0;
function selectProduct(index){productIndex=(index+cards.length)%cards.length;cards.forEach((card,i)=>{const distance=(i-productIndex+cards.length)%cards.length;card.dataset.slot=distance===0?'active':distance===1?'next':'previous';card.setAttribute('aria-hidden',String(distance!==0))});productButtons.forEach((button,i)=>button.setAttribute('aria-pressed',String(i===productIndex)));cycleElapsed=0;cycleBar.style.transform='scaleX(0)'}
function canCycle(){return !paused&&!reduced.matches&&!document.hidden&&!autoStopped&&heroVisible&&!hovering&&(!focusInHero||document.activeElement===autoButton)}
function cycle(now){cycleFrame=0;if(!canCycle())return;cycleElapsed+=Math.min(now-lastFrame,100);lastFrame=now;if(cycleElapsed>=6500)selectProduct(productIndex+1);cycleBar.style.transform=`scaleX(${cycleElapsed/6500})`;cycleFrame=requestAnimationFrame(cycle)}
function syncCycle(){const running=canCycle();showcase.classList.toggle('gallery-stopped',!running);autoButton.disabled=paused||reduced.matches;autoButton.textContent=autoStopped?'▷':'Ⅱ';autoButton.setAttribute('aria-label',autoStopped?'开启商品轮换':'暂停商品轮换');autoButton.setAttribute('aria-pressed',String(autoStopped));if(running&&!cycleFrame){lastFrame=performance.now();cycleFrame=requestAnimationFrame(cycle)}else if(!running&&cycleFrame){cancelAnimationFrame(cycleFrame);cycleFrame=0}}
productButtons.forEach((button,i)=>button.addEventListener('click',()=>{selectProduct(i);autoStopped=true;syncCycle()}));
autoButton.addEventListener('click',()=>{autoStopped=!autoStopped;syncCycle()});
gallery.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();selectProduct(productIndex+(e.key==='ArrowRight'?1:-1));autoStopped=true;syncCycle()}});
showcase.addEventListener('pointerenter',e=>{if(e.pointerType==='mouse'){hovering=true;syncCycle()}});
showcase.addEventListener('pointerleave',()=>{hovering=false;showcase.style.setProperty('--stage-rx','0deg');showcase.style.setProperty('--stage-ry','0deg');syncCycle()});
showcase.addEventListener('pointermove',e=>{if(e.pointerType!=='mouse'||paused||reduced.matches||mobile.matches)return;const r=showcase.getBoundingClientRect();showcase.style.setProperty('--stage-rx',`${-(e.clientY-r.top-r.height/2)/r.height*5}deg`);showcase.style.setProperty('--stage-ry',`${(e.clientX-r.left-r.width/2)/r.width*7}deg`)});
showcase.addEventListener('focusin',()=>{focusInHero=true;syncCycle()});
showcase.addEventListener('focusout',e=>{if(!showcase.contains(e.relatedTarget)){focusInHero=false;syncCycle()}});
new IntersectionObserver(entries=>{heroVisible=entries[0].isIntersecting;syncCycle()},{threshold:.15}).observe(showcase);
document.addEventListener('motionstatechange',syncCycle);document.addEventListener('visibilitychange',syncCycle);
selectProduct(0);syncCycle();
