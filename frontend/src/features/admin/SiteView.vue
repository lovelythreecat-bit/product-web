<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppDrawer from '../../components/AppDrawer.vue'
import AppDialog from '../../components/AppDialog.vue'
import * as api from '../../api/site'
import type { Schema } from '../../types/api'
import { useAdminRequest } from './shared'
const {busy,error,run} = useAdminRequest()
const current = ref<Schema<'SiteContentView'> | null>(null), cases = ref<Schema<'AdminCaseView'>[]>([])
const editOpen=ref(false), caseOpen=ref(false), confirmOpen=ref(false), notice=ref('')
const action=ref<'publish'|'withdraw'>('publish'), selected=ref<Schema<'AdminCaseView'> | null>(null)
const expected=ref(0), intro=ref(''), text=ref(''), image=ref(''), video=ref(''), steps=ref('')
const d11=ref(''), d07=ref(''), d12=ref('')
const workId=ref(''), authorization=ref(''), caseD11=ref(''), caseD07=ref(''), caseD12=ref(''), withdrawPolicy=ref('')
function load() { return run(() => Promise.all([api.getAdminSiteContent(),api.getAdminCases()]), ([site,items])=>{current.value=site;cases.value=items}) }
function edit() {
 const row=current.value;if(!row)return
 expected.value=row.version;intro.value=row.content?.product_intro??'';text.value=row.content?.agent_descriptions.text??'';image.value=row.content?.agent_descriptions.image??'';video.value=row.content?.agent_descriptions.video??'';steps.value=row.content?.process_steps.join('\n')??''
 d11.value=row.policy_version;d07.value=row.policy_versions['D-07']??'';d12.value=row.policy_versions['D-12']??'';error.value='';editOpen.value=true
}
async function save() {
 const ok=await run(()=>api.updateSiteContent({expected_version:expected.value,content:{product_intro:intro.value,agent_descriptions:{text:text.value,image:image.value,video:video.value},process_steps:steps.value.split('\n').map(x=>x.trim()).filter(Boolean)},policy_version:d11.value,policy_versions:{...(d07.value?{'D-07':d07.value}:{}),...(d12.value?{'D-12':d12.value}:{})}}),row=>{current.value=row;editOpen.value=false;notice.value=row.status==='approved'?'已保存批准版本。':'草稿已保存，尚未公开。'})
 return ok
}
function newCase(){workId.value='';authorization.value='';caseD11.value='';caseD07.value='';caseD12.value='';error.value='';caseOpen.value=true}
function preparePublish(){action.value='publish';confirmOpen.value=true;error.value=''}
function prepareWithdraw(row: Schema<'AdminCaseView'>){selected.value=row;withdrawPolicy.value=row.state==='cleanup_pending'?(row.withdrawal_policy_version??''):row.policy_version;action.value='withdraw';confirmOpen.value=true;error.value=''}
async function confirm(){
 const ok=action.value==='publish'
 ? await run(()=>api.publishCase({work_id:workId.value,authorization_ref:authorization.value,policy_version:caseD11.value,policy_versions:{'D-07':caseD07.value,'D-12':caseD12.value}}),()=>{caseOpen.value=false;notice.value='已按独立授权创建公开副本。'})
 : await run(()=>api.withdrawCase(selected.value!.id,withdrawPolicy.value),row=>{notice.value=row.state==='withdrawn'?'案例已下架，公开副本已清理。':'案例已下架，副本清理待重试。'})
 if(ok){confirmOpen.value=false;await load()}
}
onMounted(load)
</script>
<template>
 <div class="admin-page"><header class="page-heading"><h1>官网内容</h1><p>维护产品介绍与取得独立公开授权的真实案例。</p></header><p v-if="error" class="field-error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p><button class="button" :disabled="busy" @click="load">刷新当前记录</button>
 <section class="panel"><div class="section-heading"><h2>产品介绍</h2><button class="button primary" :disabled="busy||!current" @click="edit">编辑介绍</button></div><template v-if="current"><p>版本 {{ current.version }} · {{ current.status==='approved'?'已批准':'草稿' }}</p><p class="site-summary">{{ current.content?.product_intro || '尚未填写产品介绍。' }}</p><details><summary>公开批准说明</summary><p>保存编辑不会代替运营批准。公开内容需已确认的 D-07、D-11、D-12 政策，且 D-11 的 content_ref 必须与本版本内容摘要一致。mock 环境也不公开草稿。</p><p class="site-ref">内容引用：{{ current.content_ref || '保存后生成' }}</p></details><RouterLink to="/">查看公开首页</RouterLink></template></section>
 <section class="panel"><div class="section-heading"><h2>真实案例</h2><button class="button primary" :disabled="busy" @click="newCase">添加授权案例</button></div><p>只接受明确批准的作品来源、归属与公开展示依据；普通内容访问授权不能替代。最近 100 条记录。</p><div v-if="cases.length" class="admin-table" tabindex="0" role="region" aria-label="案例记录，可横向滚动"><table><thead><tr><th>来源作品 / 归属</th><th>授权依据</th><th>政策版本</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="row in cases" :key="row.id"><td>{{ row.work_id }}<small>{{ row.owner_id }}</small></td><td>{{ row.authorization_ref }}</td><td>{{ row.policy_version }}</td><td>{{ row.state==='published'?'公开中':row.state==='cleanup_pending'?'已下架 · 待清理':'已撤回' }}</td><td><button v-if="row.state!=='withdrawn'" class="button" :disabled="busy" @click="prepareWithdraw(row)">{{ row.state==='cleanup_pending'?'重试清理':'撤回案例' }}</button></td></tr></tbody></table></div><p v-else>暂无真实案例授权材料。取得授权后再添加。</p></section></div>
 <AppDrawer v-model:open="editOpen" title="编辑官网介绍" purpose="edit"><form id="site-editor" class="form-stack" @submit.prevent="save"><p>保存基线：版本 {{ expected }}。未获匹配批准的内容会保存为草稿。</p><label>产品介绍<textarea v-model="intro" required maxlength="5000" rows="5" data-initial-focus /></label><label>文案 Agent<textarea v-model="text" required maxlength="5000" rows="3" /></label><label>图片 Agent<textarea v-model="image" required maxlength="5000" rows="3" /></label><label>视频 Agent<textarea v-model="video" required maxlength="5000" rows="3" /></label><label>使用流程（每行一步，最多 12 步）<textarea v-model="steps" required rows="5" /></label><label>D-11 政策版本（可为待确认草稿）<input v-model="d11" required pattern="[\w.-]+" maxlength="128"></label><details><summary>已确认公开政策</summary><label>D-07 登录帮助版本<input v-model="d07" pattern="[\w.-]+" maxlength="128"></label><label>D-12 部署与公开说明版本<input v-model="d12" pattern="[\w.-]+" maxlength="128"></label></details><p v-if="error" class="field-error" role="alert">{{ error }}</p><button type="button" class="button" :disabled="busy" @click="load">核对最新版本（保留输入）</button><template v-if="current && current.version!==expected"><p>服务端已是版本 {{ current.version }}。请核对后明确采用新基线；当前输入不会被替换。</p><p class="site-summary">当前产品介绍：{{ current.content?.product_intro }}</p><details><summary>查看当前 Agent 介绍与流程</summary><p>{{ current.content?.agent_descriptions.text }}</p><p>{{ current.content?.agent_descriptions.image }}</p><p>{{ current.content?.agent_descriptions.video }}</p><ol><li v-for="(step,i) in current.content?.process_steps" :key="i">{{ step }}</li></ol></details><button type="button" class="button" :disabled="busy" @click="expected=current.version">已核对，采用版本 {{ current.version }} 为基线</button></template></form><template #actions><button class="button primary" form="site-editor" :disabled="busy">保存介绍版本</button></template></AppDrawer>
 <AppDrawer v-model:open="caseOpen" title="添加授权案例" purpose="edit"><form id="case-editor" class="form-stack" @submit.prevent="preparePublish"><p>政策必须绑定该作品 ID、原归属与授权引用，并明确副本与撤回规则。模拟成果无法发布为真实案例。</p><label>来源作品 ID<input v-model="workId" required data-initial-focus></label><label>独立公开展示授权引用<input v-model="authorization" required maxlength="1024"></label><label>D-11 已确认版本<input v-model="caseD11" required pattern="[\w.-]+"></label><label>D-07 已确认版本<input v-model="caseD07" required pattern="[\w.-]+"></label><label>D-12 已确认版本<input v-model="caseD12" required pattern="[\w.-]+"></label><p v-if="error" class="field-error" role="alert">{{ error }}</p></form><template #actions><button class="button primary" form="case-editor" :disabled="busy">核对并发布</button></template></AppDrawer>
 <AppDialog v-model:open="confirmOpen" :title="action==='publish'?'确认发布授权案例':'确认撤回案例'" purpose="delete"><template v-if="action==='publish'"><p>将为作品 {{ workId }} 创建独立公开副本。来源、归属、授权与政策由服务端核验。</p></template><template v-else><p>将下架案例 {{ selected?.id }}，按明确批准的规则清理公开副本。私有原作不变。</p><label>撤回依据 D-11 版本<input v-model="withdrawPolicy" required></label></template><p v-if="error" class="field-error" role="alert">{{ error }}</p><template #actions><button class="button danger" :disabled="busy || (action==='withdraw'&&!withdrawPolicy.trim())" @click="confirm">{{ action==='publish'?'发布公开副本':'撤回并清理' }}</button></template></AppDialog>
</template>
<style scoped>.admin-page{grid-template-columns:minmax(0,1fr)}.site-summary{white-space:pre-wrap;overflow-wrap:anywhere}.site-ref{overflow-wrap:anywhere}.admin-table td{overflow-wrap:anywhere}details label{display:grid;gap:8px;margin-top:16px}</style>
