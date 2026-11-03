const root=document.documentElement;
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const params=new URLSearchParams(location.search);
root.dataset.theme=params.get('theme')==='light'?'light':'dark';
window.exhibition={paused:reduced.matches,reduced:reduced.matches,mode:'beginner',replay:0};
const theme=document.querySelector('#theme');
function themeLabel(){theme.setAttribute('aria-label',root.dataset.theme==='dark'?'切换浅色主题':'切换深色主题');}
themeLabel();
theme.addEventListener('click',()=>{root.dataset.theme=root.dataset.theme==='dark'?'light':'dark';themeLabel();const url=new URL(location);url.searchParams.set('theme',root.dataset.theme);history.replaceState(null,'',url);dispatchEvent(new Event('exhibitionchange'));});
const motion=document.querySelector('#motion');
function motionLabel(){motion.textContent=reduced.matches?'已减少动态效果':window.exhibition.paused?'播放动效 ▷':'暂停动效 Ⅱ';motion.disabled=reduced.matches;motion.setAttribute('aria-pressed',String(window.exhibition.paused));const replay=document.querySelector('#replay');replay.disabled=window.exhibition.paused;replay.title=window.exhibition.paused?'开启动态效果后可重播':'';}
motionLabel();
motion.addEventListener('click',()=>{window.exhibition.paused=!window.exhibition.paused;motionLabel();dispatchEvent(new Event('exhibitionchange'));});
reduced.addEventListener('change',()=>{window.exhibition.reduced=reduced.matches;window.exhibition.paused=reduced.matches;motionLabel();dispatchEvent(new Event('exhibitionchange'));});
document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>{window.exhibition.mode=button.dataset.mode;document.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));document.querySelector('#beginner').hidden=button.dataset.mode!=='beginner';document.querySelector('#pro').hidden=button.dataset.mode!=='pro';dispatchEvent(new Event('exhibitionchange'));}));
document.querySelector('#replay').addEventListener('click',()=>{window.exhibition.replay++;dispatchEvent(new Event('exhibitionchange'));});
const dialog=document.querySelector('dialog');
document.querySelectorAll('[data-preview]').forEach(button=>button.addEventListener('click',()=>dialog.showModal()));
document.querySelectorAll('.close-dialog,.close-action').forEach(button=>button.addEventListener('click',()=>dialog.close()));
dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
