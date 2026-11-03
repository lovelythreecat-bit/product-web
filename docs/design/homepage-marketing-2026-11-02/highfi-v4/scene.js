import * as T from './vendor/three.module.min.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

const host=document.querySelector('#scene');
const state=window.exhibition;
const root=document.documentElement;
let renderer;
try {renderer=new T.WebGLRenderer({alpha:true,antialias:true,powerPreference:'high-performance'});}catch(error){root.dataset.renderer='fallback';document.querySelector('#stage-title').textContent='静态商品示例';console.warn('WebGL unavailable',error);}
if(renderer) start().catch(error=>{root.dataset.renderer='fallback';root.dataset.assetError='product-model';document.querySelector('#stage-title').textContent='静态商品示例';console.error(error);});

async function start(){
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
renderer.setClearColor(0x000000,0);
renderer.outputColorSpace=T.SRGBColorSpace;
renderer.toneMapping=T.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.12;
host.appendChild(renderer.domElement);
const scene=new T.Scene();
const camera=new T.PerspectiveCamera(36,1,.1,80);
camera.position.set(0,1,13);
const world=new T.Group();scene.add(world);
const envScene=new T.Scene();envScene.background=new T.Color('#727b8a');
function softbox(w,h,x,y,z,color,intensity=1){const m=new T.Mesh(new T.PlaneGeometry(w,h),new T.MeshBasicMaterial({color,side:T.DoubleSide}));m.material.color.multiplyScalar(intensity);m.position.set(x,y,z);m.lookAt(0,0,0);envScene.add(m);}
softbox(4,12,-5,3,3,'#ffffff',2);softbox(3,9,6,2,0,'#d6e4ff',1.5);softbox(7,3,0,8,0,'#ffffff',2);softbox(2,6,1,0,-7,'#9cbcff',1.2);
const pmrem=new T.PMREMGenerator(renderer);const environment=pmrem.fromScene(envScene,.025);scene.environment=environment.texture;pmrem.dispose();
scene.add(new T.HemisphereLight(0xf2f5ff,0x34425b,1.3));
const key=new T.DirectionalLight(0xffffff,2.6);key.position.set(-3,5,7);scene.add(key);
const rim=new T.DirectionalLight(0xadc9ff,1.5);rim.position.set(4,2,-4);scene.add(rim);
const fill=new T.DirectionalLight(0xe3ecff,.8);fill.position.set(-5,-1,0);scene.add(fill);
const mat=(color,metalness=.0,roughness=.3)=>new T.MeshStandardMaterial({color,metalness,roughness});
const chrome=mat('#b9c9df',1,.16),blue=new T.MeshPhysicalMaterial({color:'#0638cf',metalness:.65,roughness:.2,clearcoat:1,clearcoatRoughness:.12});
const black=mat('#0b1425',.25,.24),white=mat('#e8edf5',.12,.19);
function mesh(geo,material,parent=world){const m=new T.Mesh(geo,material);parent.add(m);return m;}
function canvasTexture(w,h,draw){const c=document.createElement('canvas');c.width=w;c.height=h;draw(c.getContext('2d'),w,h);const t=new T.CanvasTexture(c);t.colorSpace=T.SRGBColorSpace;return t;}
// Shopify MaterialsVariantsShoe, CC BY 4.0. See assets/ATTRIBUTION.md.
// Preserve its authored fabric, normal, occlusion and roughness maps.
const gltf=await new GLTFLoader().loadAsync('./assets/studio-shoe.glb');
const shoeMaterials=await Promise.all([0,1,2].map(i=>gltf.parser.getDependency('material',i)));
const bounds=new T.Box3().setFromObject(gltf.scene);const center=bounds.getCenter(new T.Vector3());const dimensions=bounds.getSize(new T.Vector3());
const shoeTemplate=new T.Group();gltf.scene.position.sub(center);shoeTemplate.add(gltf.scene);shoeTemplate.scale.setScalar(4.5/dimensions.x);
for(const material of shoeMaterials){material.envMapIntensity=.7;for(const texture of [material.map,material.normalMap,material.roughnessMap,material.aoMap])if(texture)texture.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());}
function shoe(variant=1){const g=new T.Group();const model=shoeTemplate.clone(true);model.traverse(n=>{if(n.isMesh)n.material=shoeMaterials[variant];});g.add(model);return g;}
const product=shoe(1);world.add(product);
const companion=shoe(0);world.add(companion);
const platform=new T.Group();world.add(platform);
const shadowTexture=canvasTexture(256,256,(c)=>{const gradient=c.createRadialGradient(128,128,20,128,128,128);gradient.addColorStop(0,'rgba(10,31,70,.5)');gradient.addColorStop(1,'rgba(10,31,70,0)');c.fillStyle=gradient;c.fillRect(0,0,256,256);});
const floor=mesh(new T.PlaneGeometry(8,8),new T.MeshBasicMaterial({map:shadowTexture,transparent:true,depthWrite:false}),platform);floor.rotation.x=-Math.PI/2;floor.position.y=-2.24;
// The same actual product model is photographed into render targets for the output sheets.
// These are generated scene textures, not a background image substituted for the 3D product.
const targets=[];
function photograph(index){
 const s=new T.Scene();s.background=new T.Color(['#e8e9e9','#18304f','#c9d8e7'][index]);s.environment=environment.texture;
 s.add(new T.HemisphereLight(0xffffff,0x6e86a8,1.3));const l=new T.DirectionalLight(0xffffff,2.6);l.position.set(-3,6,4);s.add(l);
 const p=shoe(index===1?0:1);p.scale.setScalar(.76);p.rotation.set([.15,.3,-.08][index],[-.3,.45,-.8][index],[.38,-.28,.52][index]);p.position.y=.05;s.add(p);
 const shadow=mesh(new T.PlaneGeometry(6,6),new T.MeshBasicMaterial({map:shadowTexture,transparent:true,depthWrite:false}),s);shadow.rotation.x=-Math.PI/2;shadow.position.y=-1.45;
 const cam=new T.PerspectiveCamera(35,.78,.1,30);cam.position.set(.0,.4,9.4);cam.lookAt(0,0,0);
 const target=new T.WebGLRenderTarget(640,820);targets.push(target);renderer.setRenderTarget(target);renderer.render(s,cam);renderer.setRenderTarget(null);return target.texture;
}
const photoTextures=[0,1,2].map(photograph);
const gallery=new T.Group();world.add(gallery);
function panel(w,h,texture,parent=gallery){const g=new T.Group();const edge=mesh(new T.BoxGeometry(w+.06,h+.06,.075),chrome,g);const p=mesh(new T.PlaneGeometry(w,h),new T.MeshBasicMaterial({map:texture,side:T.DoubleSide}),g);p.position.z=.041;parent.add(g);return g;}
const sheets=[panel(1.8,2.3,photoTextures[0]),panel(1.8,2.3,photoTextures[1]),panel(1.8,2.3,photoTextures[2])];
const video=new T.Group();world.add(video);
const phones=[];
for(let i=0;i<3;i++){
 const g=new T.Group();video.add(g);mesh(new T.BoxGeometry(1.40,2.70,.14),chrome,g);const face=mesh(new T.PlaneGeometry(1.32,2.62),black,g);face.position.z=.076;
 const screen=mesh(new T.PlaneGeometry(1.23,2.38),new T.MeshBasicMaterial({map:photoTextures[i]}),g);screen.position.set(0,.03,.081);
 const notch=mesh(new T.CapsuleGeometry(.035,.22,4,10),black,g);notch.rotation.z=Math.PI/2;notch.position.set(0,1.22,.09);
 const line=mesh(new T.PlaneGeometry(.8,.018),new T.MeshBasicMaterial({color:'#ffffff'}),g);line.position.set(0,-1.06,.092);
 const time=mesh(new T.PlaneGeometry(.23,.028),new T.MeshBasicMaterial({color:'#659fff'}),g);time.position.set(-.28,-1.06,.094);g.userData.time=time;
 phones.push(g);
}
const storyboardRail=mesh(new T.TorusGeometry(3.25,.012,8,120,Math.PI*1.6),new T.MeshBasicMaterial({color:'#567bb4'}),video);storyboardRail.rotation.set(1.4,.2,.5);storyboardRail.position.y=-1.8;
const guidance=new T.Group();world.add(guidance);
const loader=new T.TextureLoader();let texturesPending=1;
const lingling=loader.load('../highfi-v3/assets/lingling.png',()=>{texturesPending--;invalidate();},undefined,()=>{texturesPending--;root.dataset.assetError='lingling';invalidate();});lingling.colorSpace=T.SRGBColorSpace;
const character=mesh(new T.PlaneGeometry(3.0,4.5),new T.MeshBasicMaterial({map:lingling,transparent:true,depthWrite:false,side:T.DoubleSide,toneMapped:false}),guidance);character.position.set(.15,.2,.65);
const guideHalo=new T.Group();guidance.add(guideHalo);
const tiles=[];
for(let i=0;i<3;i++){const tile=panel(.8,1.05,photoTextures[i],guidance);tiles.push(tile);}
const desk=new T.Group();guidance.add(desk);
const deskScreen=panel(3.6,2.3,photoTextures[1],desk);deskScreen.rotation.y=-.18;
const deskTexture=canvasTexture(1024,640,(c,w,h)=>{c.fillStyle='#111d32';c.fillRect(0,0,w,h);c.fillStyle='#85b6ff';c.font='24px sans-serif';c.fillText('专业工作台',35,52);c.fillStyle='#23334e';c.fillRect(25,90,180,520);c.fillRect(780,90,215,520);c.fillStyle='#a8bad5';c.font='18px sans-serif';['图层','参数','批量','模板'].forEach((s,i)=>{c.fillText(s,55,142+i*62);c.fillStyle='#476992';c.fillRect(805,135+i*82,155,6);c.fillStyle='#a8bad5';});c.fillStyle='#c6d6ed';c.fillRect(230,90,525,520);});
const deskUI=mesh(new T.PlaneGeometry(3.5,2.2),new T.MeshBasicMaterial({map:deskTexture}),deskScreen);deskUI.position.z=.05;const deskProduct=panel(1.25,1.6,photoTextures[0],deskScreen);deskProduct.position.set(.02,-.03,.065);
const distribution=new T.Group();world.add(distribution);
const hub=shoe(1);hub.scale.setScalar(.3);distribution.add(hub);
const shopNodes=[];
for(let i=0;i<5;i++){
 const g=new T.Group();distribution.add(g);const screen=panel(1.1,1.4,photoTextures[i%3],g);
 const roof=mesh(new T.BoxGeometry(1.24,.18,.23),blue,g);roof.position.set(0,.79,0);
 for(let j=0;j<5;j++){const stripe=mesh(new T.BoxGeometry(.12,.2,.25),white,g);stripe.position.set(-.48+j*.24,.78,.01);}
 shopNodes.push(g);
}
const routes=[];
for(let i=0;i<5;i++){const a=i*Math.PI*2/5;const end=new T.Vector3(Math.cos(a)*2.55,Math.sin(a)*1.65,-.6+Math.sin(a)*.4);const curve=new T.QuadraticBezierCurve3(new T.Vector3(0,0,0),new T.Vector3(end.x*.35,end.y*.5,1.25),end);const line=mesh(new T.TubeGeometry(curve,36,.009,6,false),new T.MeshBasicMaterial({color:'#679bff',transparent:true,opacity:.65}),distribution);const dot=mesh(new T.SphereGeometry(.045,12,8),new T.MeshBasicMaterial({color:'#b8d8ff'}),distribution);routes.push({curve,dot});}
const chapters=[...document.querySelectorAll('.chapter')];
const nav=[...document.querySelectorAll('.chapter-index a')];
const titles=['商品创作展厅','一件商品，多种表达','卖点进入，分镜展开','玲玲陪你，一步步出片','一套素材，连接多个店铺','让每个电商人，都拥有内容工厂'];
let active=-1,scrollTarget=0,progress=0,clock=0,last=performance.now(),raf=0,dirty=true,lastTheme='',lastReplay=state.replay,replayStart=-10;
const pointer=new T.Vector2(),smoothedPointer=new T.Vector2();
function updateScroll(){const y=scrollY;let p=0;for(let i=0;i<chapters.length-1;i++){const a=chapters[i].offsetTop,b=chapters[i+1].offsetTop;if(y>=a)p=i+T.MathUtils.clamp((y-a)/(b-a),0,1);}scrollTarget=T.MathUtils.clamp(p,0,5);if(state.paused||state.reduced)progress=Math.round(scrollTarget);invalidate();}
function resize(){const r=host.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();invalidate();}
function invalidate(){dirty=true;if(!raf&&!document.hidden)raf=requestAnimationFrame(frame);}
addEventListener('scroll',updateScroll,{passive:true});addEventListener('resize',()=>{resize();updateScroll();});new ResizeObserver(resize).observe(host);
addEventListener('pointermove',e=>{if(e.pointerType==='mouse'&&!state.paused&&!state.reduced){pointer.set(e.clientX/innerWidth*2-1,e.clientY/innerHeight*2-1);invalidate();}},{passive:true});
addEventListener('exhibitionchange',()=>{if(state.paused||state.reduced){progress=Math.round(scrollTarget);pointer.set(0,0);smoothedPointer.set(0,0);}invalidate();});
document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelAnimationFrame(raf);raf=0;}else{last=performance.now();invalidate();}});
renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();root.dataset.renderer='fallback';cancelAnimationFrame(raf);raf=0;document.querySelector('#stage-title').textContent='静态商品示例';});
renderer.domElement.addEventListener('webglcontextrestored',()=>location.reload());
function weight(i){return Math.max(0,1-Math.abs(progress-i));}
function place(obj,position,rotation,scale=1){obj.position.set(...position);obj.rotation.set(...rotation);obj.scale.setScalar(Math.max(.0001,scale));obj.visible=scale>.002;}
function frame(now){
 raf=0;const dt=Math.max(0,Math.min((now-last)/1000,.05));last=now;
 const moving=!state.paused&&!state.reduced;
 if(moving){clock+=dt;progress=T.MathUtils.lerp(progress,scrollTarget,1-Math.exp(-dt*9));smoothedPointer.lerp(pointer,1-Math.exp(-dt*3));}
 if(Math.abs(progress-scrollTarget)<.0001)progress=scrollTarget;
 const n=Math.min(5,Math.round(scrollTarget));
 if(n!==active){active=n;document.body.dataset.active=String(n);nav.forEach((a,i)=>i===n?a.setAttribute('aria-current','location'):a.removeAttribute('aria-current'));document.querySelector('#stage-title').textContent=titles[n];}
 const theme=root.dataset.theme;
 if(theme!==lastTheme){lastTheme=theme;renderer.toneMappingExposure=theme==='light'?1.04:1.02;}
 const w=[0,1,2,3,4,5].map(weight),mobile=innerWidth<=760;
 const drift=Math.sin(clock*.65)*.07;
 world.rotation.set(smoothedPointer.y*.035,smoothedPointer.x*.065,0);
 const baseZ=mobile?13.6:12.8;
 camera.position.set(Math.sin(progress*.9)*.48+smoothedPointer.x*.18,.5+w[1]*.7+w[2]*.18,baseZ-w[0]*1.2+w[4]*.8-w[5]*.4);
 camera.lookAt(0,.05,0);
 const heroW=w[0]+w[5];
 place(product,[.15-w[1]*2.25,-.45+w[1]*.55+drift,.7],[.18,-.35+Math.sin(clock*.3)*.22+progress*.15,-.29+w[1]*.5],heroW*1.07+w[1]*.46);
 place(companion,[-.25,1.15-drift,-1.15],[.38,.55+Math.sin(clock*.24)*.12,.24],heroW*.72);
 place(platform,[0,0,0],[0,0,0],heroW+w[1]*.85+w[3]*.8);
 place(gallery,[.55,-.05,.4-(1-w[1])*3.5],[0,-.08+(1-w[1])*.55,0],w[1]);
 sheets.forEach((p,i)=>{const x=(i-1)*(.2+1.42*w[1]);place(p,[x,(i===1?.15:-.15)+drift*(i+1),i===1?.7:-.2],[.03,(i-1)*-.28,(i-1)*-.12],1);});
 place(video,[0,.0,.3-(1-w[2])*3.5],[0,.1-(1-w[2])*.6,0],w[2]);
 if(lastReplay!==state.replay){lastReplay=state.replay;replayStart=clock;}
 const replay=Math.max(0,1-(clock-replayStart)/2);
 phones.forEach((p,i)=>{const x=(i-1)*(.2+1.45*w[2]);place(p,[x,Math.sin(clock*.8+i)*.1+(i===1?.25:-.25),i===1?.65:-.45],[.03,(i-1)*-.3+(replay*Math.PI*2),(i-1)*-.10],i===1?1.12:.87);p.userData.time.scale.x=1+.7*Math.sin(clock*1.2+i);});
 place(guidance,[0,-.05,.4],[0,-.05,0],w[3]);
 const pro=state.mode==='pro';character.visible=!pro;guideHalo.visible=!pro;desk.visible=pro;desk.rotation.set(.08,-.12,.02);desk.position.set(0,.15,.6);
 tiles.forEach((p,i)=>{const a=clock*.12+i*2.1;place(p,[Math.cos(a)*2.04,Math.sin(a)*1.2,-.5],[0,-Math.cos(a)*.25,Math.sin(a)*.1],pro?.45:.8);});
 place(distribution,[0,.0,0],[0,-.16+Math.sin(clock*.15)*.05,0],w[4]);
 hub.rotation.set(.15,-.3+Math.sin(clock*.25)*.2,-.25);
 shopNodes.forEach((p,i)=>{const a=i*Math.PI*2/5;place(p,[Math.cos(a)*2.55,Math.sin(a)*1.65,-.6+Math.sin(a)*.4],[0,-Math.cos(a)*.18,Math.cos(a)*.06],.84);routes[i].dot.position.copy(routes[i].curve.getPoint((clock*.22+i*.2)%1));});
 if(moving||dirty||texturesPending){renderer.render(scene,camera);root.dataset.renderer='webgl';dirty=false;}
 // Small read-only diagnostics for checking actual motion and graceful degradation.
 window.exhibitionDiagnostics={renderer:'WebGL',model:'Shopify MaterialsVariantsShoe',scene:active,progress:+progress.toFixed(3),time:+clock.toFixed(3),camera:camera.position.toArray(),productRotation:product.rotation.toArray().slice(0,3),drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,mode:state.mode,paused:state.paused,reduced:state.reduced,texturesPending};
 if(moving||texturesPending)raf=requestAnimationFrame(frame);
}
resize();updateScroll();invalidate();
}
