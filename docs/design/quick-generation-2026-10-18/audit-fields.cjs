/* Snapshot only existing product UI fields; no application source is changed. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../..'),ts=require(path.join(root,'frontend/node_modules/typescript'));
const source=p=>fs.readFileSync(path.join(root,p),'utf8');
function load(p,deps={}){const module={exports:{}};const output=ts.transpileModule(source(p),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;new Function('require','module','exports',output)(n=>{assert.ok(n in deps,n);return deps[n]},module,module.exports);return module.exports;}
const products=load('frontend/src/features/workspace/productTypes.ts');
const display=load('frontend/src/features/workspace/display.ts',{'./productTypes':products});
const text=source('frontend/src/features/workspace/TextChoices.vue'),media=source('frontend/src/features/workspace/MediaChoices.vue');
function array(text,name){const literal=text.match(new RegExp('const '+name+' = (\\[[^\\n]+)'))?.[1];assert.ok(literal,name);return new Function('return ('+literal+')')();}
const textKeys=[...text.matchAll(/update\('([^']+)'/g)].map(m=>m[1]);
const textLabels=['文案类型','目标平台','目标人群','语气','最大字符数','额外协作要求'];assert.equal(textKeys.length,textLabels.length);
const plan=source('frontend/src/features/workspace/VideoTaskPanel.vue');
const planKeys=[...plan.matchAll(/viewedPlan\.document\.(\w+)/g)].map(m=>m[1]);
const contract={productKinds:products.productTypes.map(t=>[t.value,t.label]),kindFields:Object.fromEntries(products.productTypes.map(t=>[t.value,t.fields])),productGroups:Object.fromEntries(products.productTypes.map(t=>[t.value,products.productFormGroups(t.value)])),productNames:display.productLabels,longProductFields:products.longProductFields,textFields:textKeys.map((k,i)=>[k,textLabels[i]]),textSuggestions:{copy_type:array(text,'copyTypes'),platform:array(text,'platforms'),tone:array(text,'tones')},platforms:array(media,'platforms'),imageOutputs:[...media.matchAll(/<option value="([^"]+)">([^<]+)<\/option>/g)].map(m=>[m[1],m[2]]),videoPlanKeys:[...new Set(planKeys)]};
fs.writeFileSync(path.join(__dirname,'field-contract.js'),'// Generated from the existing workspace sources by audit-fields.cjs.\nwindow.quickGenerationFields = '+JSON.stringify(contract,null,2)+';\n');
fs.writeFileSync(path.join(__dirname,'field-audit.json'),JSON.stringify({status:'existing-fields-only',sources:['productTypes.ts','display.ts','TextChoices.vue','MediaChoices.vue','VideoTaskPanel.vue','PromptEditor.vue'].map(x=>'frontend/src/features/workspace/'+x),productTypes:contract.productKinds.length,textFields:contract.textFields,imagePlatforms:contract.platforms,videoParameters:['first_frame_file_id'],instruction:'instruction',removed:['数码电子商品摘要中的独立颜色字段','生成成果直接作为视频首帧选项','自造的视频方案字段：首帧、画面安排、创作依据、节奏要求、声音'],renamed:{'屏幕规格':'屏幕参数','电池 / 续航':'电池与续航','兼容性':'兼容设备','促销信息':'优惠信息','售后政策':'售后保障','图片创作要求':'创作指令','视频创作要求':'创作指令'},scope:'Prototype only; workflow controls and reviewed-copy confirmation belong to the requested new flow.'},null,2));
console.log(`Field contract refreshed: ${contract.productKinds.length} product types, ${textKeys.length} text inputs, ${contract.platforms.length} image platforms; video input remains first_frame_file_id + instruction.`);
