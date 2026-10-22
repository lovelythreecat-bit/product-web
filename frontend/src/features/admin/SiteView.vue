<script setup lang="ts">
import { ElTable, ElTableColumn } from 'element-plus/es/components/table/index'
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import { onMounted, ref } from 'vue'
import AppDrawer from '../../components/AppDrawer.vue'
import AppDialog from '../../components/AppDialog.vue'
import * as api from '../../api/site'
import type { Schema } from '../../types/api'
import { useAdminRequest } from './shared'
import { useUserAccounts } from './userAccounts'
const {busy,error,run} = useAdminRequest()
const { load: loadUserAccounts, accountName, error: accountsError } = useUserAccounts()
const current = ref<Schema<'SiteContentView'> | null>(null), cases = ref<Schema<'AdminCaseView'>[]>([])
const editOpen=ref(false), caseOpen=ref(false), confirmOpen=ref(false), notice=ref('')
const action=ref<'publish'|'withdraw'>('publish'), selected=ref<Schema<'AdminCaseView'> | null>(null)
const expected=ref(0), intro=ref(''), text=ref(''), image=ref(''), video=ref(''), steps=ref('')
const d11=ref(''), d07=ref(''), d12=ref('')
const workId=ref(''), authorization=ref(''), caseD11=ref(''), caseD07=ref(''), caseD12=ref(''), withdrawPolicy=ref('')
function load() { return run(() => Promise.all([api.getAdminSiteContent(),api.getAdminCases()]), ([site,items])=>{current.value=site;cases.value=items}) }
async function edit() {
 if(!await load())return
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
onMounted(() => { void load(); void loadUserAccounts() })
const RowColumn = ElTableColumn<Schema<'AdminCaseView'>>
</script>
<template>
 <div class="admin-page"><header class="page-heading admin-heading-with-action"><UiButton class="button" :disabled="busy" @click="load">刷新当前记录</UiButton></header><p v-if="error" class="field-error" role="alert">{{ error }}</p><p v-if="accountsError" class="field-error" role="alert">{{ accountsError }}</p><p v-if="notice" role="status">{{ notice }}</p>
 <section class="panel"><div class="section-heading"><h2>产品介绍</h2><UiButton class="button primary" :disabled="busy||!current" @click="edit">编辑介绍</UiButton></div><template v-if="current"><p>版本 {{ current.version }} · {{ current.status==='approved'?'已批准':'草稿' }}</p><p class="site-summary">{{ current.content?.product_intro || '尚未填写产品介绍。' }}</p><details><summary>公开批准说明</summary><p>保存编辑不会代替运营批准。公开内容需已确认的 D-07、D-11、D-12 政策，且 D-11 的 content_ref 必须与本版本内容摘要一致。mock 环境也不公开草稿。</p><p class="site-ref">内容引用：{{ current.content_ref || '保存后生成' }}</p></details><RouterLink class="button site-public-link" to="/">查看公开首页</RouterLink></template></section>
 <section class="panel"><div class="section-heading"><h2>真实案例</h2><UiButton class="button primary" :disabled="busy" @click="newCase">添加授权案例</UiButton></div><p>只接受明确批准的作品来源、归属与公开展示依据；普通内容访问授权不能替代。最近 100 条记录。</p><div v-if="cases.length" class="admin-table" tabindex="0" role="region" aria-label="案例记录，可横向滚动"><ElTable  :data="cases" row-key="id" class="ui-data-table" empty-text="暂无记录" border><RowColumn  :min-width="150"><template #header>来源作品 / 归属</template><template #default="{ row: row }">{{ row.work_id }}<small>{{ accountName(row.owner_id) }}</small></template></RowColumn><RowColumn  :min-width="150"><template #header>授权依据</template><template #default="{ row: row }">{{ row.authorization_ref }}</template></RowColumn><RowColumn  :min-width="150"><template #header>政策版本</template><template #default="{ row: row }">{{ row.policy_version }}</template></RowColumn><RowColumn  :min-width="150"><template #header>状态</template><template #default="{ row: row }">{{ row.state==='published'?'公开中':row.state==='cleanup_pending'?'已下架 · 待清理':'已撤回' }}</template></RowColumn><RowColumn  :min-width="150"><template #header>操作</template><template #default="{ row: row }"><UiButton v-if="row.state!=='withdrawn'" class="button" :disabled="busy" @click="prepareWithdraw(row)">{{ row.state==='cleanup_pending'?'重试清理':'撤回案例' }}</UiButton></template></RowColumn></ElTable></div><p v-else>暂无真实案例授权材料。取得授权后再添加。</p></section></div>
 <AppDrawer class="admin-overlay" v-model:open="editOpen" title="编辑官网介绍" purpose="edit"><form id="site-editor" class="form-stack" @submit.prevent="save"><p>未获匹配批准的内容会保存为草稿。</p><label>产品介绍<UiInput type="textarea" v-model="intro" required maxlength="5000" rows="5" data-initial-focus /></label><label>文案 Agent<UiInput type="textarea" v-model="text" required maxlength="5000" rows="3" /></label><label>图片 Agent<UiInput type="textarea" v-model="image" required maxlength="5000" rows="3" /></label><label>视频 Agent<UiInput type="textarea" v-model="video" required maxlength="5000" rows="3" /></label><label>使用流程（每行一步，最多 12 步）<UiInput type="textarea" v-model="steps" required rows="5" /></label><label>D-11 政策版本（可为待确认草稿）<UiInput v-model="d11" required pattern="[\w.-]+" maxlength="128" /></label><details><summary>已确认公开政策</summary><label>D-07 登录帮助版本<UiInput v-model="d07" pattern="[\w.-]+" maxlength="128" /></label><label>D-12 部署与公开说明版本<UiInput v-model="d12" pattern="[\w.-]+" maxlength="128" /></label></details><p v-if="error" class="field-error" role="alert">{{ error }}</p></form><template #actions><UiButton class="button primary" form="site-editor" :disabled="busy">保存介绍版本</UiButton></template></AppDrawer>
 <AppDrawer class="admin-overlay" v-model:open="caseOpen" title="添加授权案例" purpose="edit"><form id="case-editor" class="form-stack" @submit.prevent="preparePublish"><p>政策必须绑定该作品 ID、原归属与授权引用，并明确副本与撤回规则。模拟成果无法发布为真实案例。</p><label>来源作品 ID<UiInput v-model="workId" required data-initial-focus /></label><label>独立公开展示授权引用<UiInput v-model="authorization" required maxlength="1024" /></label><label>D-11 已确认版本<UiInput v-model="caseD11" required pattern="[\w.-]+" /></label><label>D-07 已确认版本<UiInput v-model="caseD07" required pattern="[\w.-]+" /></label><label>D-12 已确认版本<UiInput v-model="caseD12" required pattern="[\w.-]+" /></label><p v-if="error" class="field-error" role="alert">{{ error }}</p></form><template #actions><UiButton class="button primary" form="case-editor" :disabled="busy">核对并发布</UiButton></template></AppDrawer>
 <AppDialog class="admin-overlay" v-model:open="confirmOpen" :title="action==='publish'?'确认发布授权案例':'确认撤回案例'" purpose="delete"><template v-if="action==='publish'"><p>将为作品 {{ workId }} 创建独立公开副本。来源、归属、授权与政策由服务端核验。</p></template><template v-else><p>将下架案例 {{ selected?.id }}，按明确批准的规则清理公开副本。私有原作不变。</p><label>撤回依据 D-11 版本<UiInput v-model="withdrawPolicy" required /></label></template><p v-if="error" class="field-error" role="alert">{{ error }}</p><template #actions><UiButton class="button danger" :disabled="busy || (action==='withdraw'&&!withdrawPolicy.trim())" @click="confirm">{{ action==='publish'?'发布公开副本':'撤回并清理' }}</UiButton></template></AppDialog>
</template>
<style scoped>.admin-page{grid-template-columns:minmax(0,1fr)}.site-summary{white-space:pre-wrap;overflow-wrap:anywhere}.site-ref{overflow-wrap:anywhere}.admin-table td{overflow-wrap:anywhere}details label{display:grid;gap:8px;margin-top:16px}</style>
