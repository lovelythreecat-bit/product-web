const root=document.documentElement;
const themeButton=document.querySelector('.theme');
let preferred='light';
try{preferred=localStorage.getItem('feima-oil-preview-theme')||'light'}catch{}
root.dataset.theme=new URLSearchParams(location.search).get('theme')==='dark'?'dark':new URLSearchParams(location.search).get('theme')==='light'?'light':preferred;
function reflectTheme(){const dark=root.dataset.theme==='dark';themeButton.setAttribute('aria-label',`切换为${dark?'浅':'深'}色主题`);themeButton.setAttribute('title',`切换为${dark?'浅':'深'}色主题`)}
reflectTheme();
themeButton.addEventListener('click',()=>{root.dataset.theme=root.dataset.theme==='dark'?'light':'dark';try{localStorage.setItem('feima-oil-preview-theme',root.dataset.theme)}catch{}reflectTheme()});
const reduce=matchMedia('(prefers-reduced-motion: reduce)');
const tabs=[...document.querySelectorAll('[role=tab]')];
function activate(tab,focus=false){tabs.forEach(t=>{const selected=t===tab;t.setAttribute('aria-selected',selected);t.tabIndex=selected?0:-1;document.getElementById(t.getAttribute('aria-controls')).hidden=!selected});const panel=document.getElementById(tab.getAttribute('aria-controls'));if(window.gsap&&!reduce.matches)gsap.fromTo(panel,{opacity:0,y:8},{opacity:1,y:0,duration:.25,overwrite:true});if(focus)tab.focus()}
tabs.forEach((tab,i)=>{tab.addEventListener('click',()=>activate(tab));tab.addEventListener('keydown',event=>{let next=i;if(event.key==='ArrowDown'||event.key==='ArrowRight')next=(i+1)%tabs.length;else if(event.key==='ArrowUp'||event.key==='ArrowLeft')next=(i+tabs.length-1)%tabs.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=tabs.length-1;else return;event.preventDefault();activate(tabs[next],true)})});
if(window.gsap&&window.ScrollTrigger){
 gsap.registerPlugin(ScrollTrigger);
 const mm=gsap.matchMedia();
 mm.add('(prefers-reduced-motion: no-preference)',()=>{
  gsap.from('.hero-copy > *',{opacity:0,y:16,duration:.42,stagger:.045,ease:'power2.out',clearProps:'transform,opacity'});
  gsap.from('.showroom figure',{opacity:0,y:30,duration:.55,stagger:.06,delay:.18,ease:'power2.out',clearProps:'transform,opacity'});
  gsap.utils.toArray('.section-heading h2,.guide-copy h2,.steps h2,.closing h2').forEach(el=>gsap.from(el,{y:24,opacity:0,duration:.55,ease:'power3.out',scrollTrigger:{trigger:el,start:'top 92%',once:true},clearProps:'transform,opacity'}));
  gsap.utils.toArray('.gallery-grid figure').forEach(el=>gsap.from(el,{clipPath:'inset(12% 0 0 0)',opacity:.4,duration:.7,ease:'power2.out',scrollTrigger:{trigger:el,start:'top 90%',once:true},clearProps:'clipPath,opacity'}));
  gsap.from('.steps-list li',{y:18,opacity:0,stagger:.06,duration:.4,scrollTrigger:{trigger:'.steps-list',start:'top 90%',once:true},clearProps:'transform,opacity'});
 });
 mm.add('(min-width: 761px) and (prefers-reduced-motion: no-preference)',()=>{
  const spread=gsap.timeline({scrollTrigger:{trigger:'.creation-stage',start:'top 88%',end:'center 48%',scrub:.5}});
  spread.fromTo('.campaign',{x:95,rotation:0,scale:.85},{x:0,rotation:-7,scale:1,ease:'none'},0).fromTo('.detail',{x:-95,rotation:0,scale:.85},{x:0,rotation:6,scale:1,ease:'none'},0);
 });
}
