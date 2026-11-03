const root=document.documentElement;
const themeButton=document.querySelector('#theme-toggle');
const motionButton=document.querySelector('#motion-toggle');
const query=new URLSearchParams(location.search);
let theme=query.get('theme')==='light'?'light':'dark';
const setTheme=()=>{root.dataset.theme=theme;themeButton.textContent=theme==='dark'?'切换浅色':'切换深色';};
setTheme();
themeButton.addEventListener('click',()=>{theme=theme==='dark'?'light':'dark';setTheme();const url=new URL(location.href);url.searchParams.set('theme',theme);history.replaceState(null,'',url);});
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const narrow=matchMedia('(max-width: 800px)');
let motion=false;
function updateMotion(){const enabled=motion&&!reduced.matches&&!narrow.matches&&!document.hidden;root.dataset.motion=enabled?'on':'off';motionButton.textContent=reduced.matches||narrow.matches?'静态展示':motion?'暂停景深':'开启景深';motionButton.disabled=reduced.matches||narrow.matches;motionButton.setAttribute('aria-pressed',String(motion));if(!enabled){root.style.setProperty('--pointer-x','0deg');root.style.setProperty('--pointer-y','0deg');}}
motionButton.addEventListener('click',()=>{motion=!motion;updateMotion();});
reduced.addEventListener('change',updateMotion);narrow.addEventListener('change',updateMotion);document.addEventListener('visibilitychange',updateMotion);updateMotion();
let frame=0;
document.querySelector('.hero').addEventListener('pointermove',e=>{if(root.dataset.motion!=='on'||frame)return;frame=requestAnimationFrame(()=>{root.style.setProperty('--pointer-x',`${((e.clientX/innerWidth)-.5)*2.4}deg`);root.style.setProperty('--pointer-y',`${((e.clientY/innerHeight)-.5)*-1.6}deg`);frame=0;});});
document.querySelector('.hero').addEventListener('pointerleave',()=>{root.style.setProperty('--pointer-x','0deg');root.style.setProperty('--pointer-y','0deg');});
