<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import * as api from '../../api/admin'
import { ApiError } from '../../api/client'
import type { Schema } from '../../types/api'
import AppDrawer from '../../components/AppDrawer.vue'
import AppDialog from '../../components/AppDialog.vue'
import { session } from '../auth/session'
import { useAdminRequest, date, pretty } from './shared'
import { restoreGrant, rememberGrant, forgetGrant, type CreditIntent } from './creditIntent'
const {busy,error,run,current} = useAdminRequest()
const users = ref<Schema<'AdminUserView'>[]>([]), cursor = ref<string|null>(null), status = ref('')
type SelectedUser = Pick<Schema<'AdminUserView'>,'id'|'account_normalized'> & Partial<Schema<'AdminUserView'>>
const selected = ref<SelectedUser|null>(null), account = ref<Schema<'AccountView'>|null>(null)
const ledger = ref<Schema<'LedgerEntryView'>[]>([]), ledgerCursor = ref<string|null>(null), detailOpen = ref(false)
const grantOpen = ref(false), confirmOpen = ref(false), amount = ref(0), reason = ref(''), pending = ref<CreditIntent|null>(null), notice = ref('')
const actor = session.profile.value!.user_id
const pendingBody = computed<Schema<'CreditGrantRequest'>|null>(() => pending.value ? JSON.parse(pending.value.body) : null)
const config = ref<Schema<'RegistrationConfigView'>|null>(null), configOpen = ref(false)
const configDraft = ref<Schema<'RegistrationConfigUpdate'>>({expected_version:null,amount:0,policy_version:'',reason:''})
const configLoaded = ref(false)
const creatingConfig = ref(false)
const canSaveConfig = computed(() => configDraft.value.expected_version !== null
 ? configLoaded.value
 : creatingConfig.value && config.value === null)
let appliedStatus = ''
const statusOpen=ref(false), statusConfirm=ref(false), statusPolicy=ref(''), statusDraft=ref<Schema<'AccountStatusRequest'>|null>(null)
function editStatus(){if(!selected.value || selected.value.auth_version===undefined)return;statusPolicy.value='';statusDraft.value={status:selected.value.status==='active'?'disabled':'active',expected_auth_version:selected.value.auth_version,policy_version:''};statusOpen.value=true}
async function refreshSelected(){if(!selected.value)return;const target=selected.value.id;await run(async()=>{let next:string|undefined;do{const page=await api.listUsers(next);const found=page.items.find(x=>x.id===target);if(found)return found;next=page.next_cursor??undefined}while(next);throw Error('当前用户不可读取，请刷新列表。')},u=>{if(selected.value?.id===target)selected.value=u})}
async function saveStatus(){if(!selected.value||!statusDraft.value)return;const target=selected.value.id;const ok=await run(()=>api.setUserStatus(target,{...statusDraft.value!,policy_version:statusPolicy.value}),()=>{statusConfirm.value=false;statusOpen.value=false;notice.value='账户状态已更新。'});if(ok){await refreshSelected();await load()}}
function load(reset = true) { const filter=reset?status.value:appliedStatus; return run(() => api.listUsers(reset ? undefined : cursor.value ?? undefined,filter || undefined), page => { appliedStatus=filter; users.value = reset ? page.items : [...users.value,...page.items]; cursor.value = page.next_cursor }) }
function openUser(user: SelectedUser) { selected.value = user; account.value = null; ledger.value = []; ledgerCursor.value = null; detailOpen.value = true; void loadAccount(true) }
function loadAccount(reset = true) {
 const target = selected.value?.id; if (!target) return
 return run(() => Promise.all([api.userAccount(target),api.userLedger(target,reset ? undefined : ledgerCursor.value ?? undefined)]), ([balance,page]) => { if (selected.value?.id !== target) return; account.value = balance; ledger.value = reset ? page.items : [...ledger.value,...page.items]; ledgerCursor.value = page.next_cursor })
}
function editGrant() { if (!selected.value) return; amount.value = 0; reason.value = ''; notice.value = ''; grantOpen.value = true }
function confirmGrant() { if (!selected.value || !Number.isSafeInteger(amount.value) || amount.value < 0 || !reason.value.trim()) { error.value = '请填写非负整数积分及发放原因。'; return } confirmOpen.value = true }
async function sendGrant() {
 if (busy.value) return
 try { if (!pending.value) pending.value = rememberGrant(actor,{user_id:selected.value!.id,amount:amount.value,reason:reason.value.trim()}) }
 catch (e) { error.value = e instanceof Error ? e.message : '无法保存发放意图，本次未发送。'; return }
 const intent = pending.value!, input = JSON.parse(intent.body) as Schema<'CreditGrantRequest'>
 const confirmed = await run(async () => {
  try {
   const receipt = await api.grantCredits(intent)
   if (receipt.business_key !== input.business_key || receipt.user_id !== input.user_id || receipt.amount !== input.amount || receipt.reason !== input.reason || receipt.actor_id !== actor || !receipt.id) throw new Error('回执不足以确认原发放，原业务标识已保留，请同键核对重试。')
   return receipt
  } catch(e) {
   // Auth/CSRF/404 rejection of a retry cannot prove the original grant failed.
   if (current() && e instanceof ApiError && e.code && e.status === 422) { forgetGrant(actor,intent.key); pending.value = null }
   throw e
  }
 }, receipt => { forgetGrant(actor,intent.key); pending.value = null; notice.value = '发放已确认：' + receipt.amount + ' 积分 · 流水关联 ' + receipt.id; grantOpen.value = false; confirmOpen.value = false })
 if (confirmed && current() && selected.value?.id === input.user_id) await loadAccount(true)
}
function inspectPending() {
 if (!pendingBody.value) return
 const u = users.value.find(x => x.id === pendingBody.value!.user_id)
 openUser(u ?? {id:pendingBody.value.user_id,account_normalized:pendingBody.value.user_id})
}
async function editConfig() {
 creatingConfig.value = false
 configOpen.value = true
 await run(api.registrationConfig,result => { config.value=result; configLoaded.value=true; configDraft.value={expected_version:result.version,amount:result.amount,policy_version:result.policy_version,reason:''} })
}
function refreshConfig() { return run(api.registrationConfig, result => { config.value=result; configLoaded.value=true }) }
function createFirstConfig() {
 if (busy.value || config.value || configDraft.value.expected_version !== null) return
 // Explicit intent only: a failed GET is not evidence that no head exists.
 creatingConfig.value = true
}
function adoptVersion() { if (config.value) { configDraft.value.expected_version=config.value.version; creatingConfig.value=false } }
function saveConfig() { if (!canSaveConfig.value) return; return run(() => api.saveRegistrationConfig({...configDraft.value}),result => { config.value=result;configLoaded.value=true;creatingConfig.value=false;configOpen.value=false;notice.value='注册赠送配置已保存，仅影响后续新注册。' }) }
onMounted(() => { try { pending.value=restoreGrant(actor) } catch(e) { notice.value=e instanceof Error ? e.message : '本地记录无法读取。' } void load() })
</script>
<template>
 <div class="admin-page"><header class="page-heading"><h1>用户与积分</h1><p>查阅指定用户账户，按原因发放积分并保留账目。</p></header>
 <p v-if="error" role="alert" class="field-error">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
 <section v-if="pendingBody" class="panel"><h2>有一笔发放待核对</h2><p>目标 {{ pendingBody.user_id }} · {{ pendingBody.amount }} 积分</p><p>{{ pendingBody.reason }}</p><p>业务标识：{{ pendingBody.business_key }}</p><p>响应不明时请查询目标流水或同键重试，避免另建发放。</p><div class="action-row"><button class="button" :disabled="busy" @click="inspectPending">核对目标账户</button><button class="button primary" :disabled="busy" @click="sendGrant">同键重试发放</button></div></section>
 <section class="panel"><div class="section-heading"><h2>用户列表</h2><button class="button" :disabled="busy" @click="editConfig">注册赠送配置</button></div><form class="admin-filters" @submit.prevent="load()"><label>账户状态<select v-model="status"><option value="">全部</option><option value="active">正常</option><option value="disabled">已停用</option></select></label><button class="button" :disabled="busy">查询用户</button></form><p v-if="busy" role="status">正在处理…</p><div class="admin-table"><table><thead><tr><th>账号</th><th>角色</th><th>状态</th><th>注册时间</th><th>操作</th></tr></thead><tbody><tr v-for="user in users" :key="user.id"><td>{{ user.account_normalized }}<small>{{ user.nickname }}</small></td><td>{{ user.role === 'admin' ? '管理员' : '用户' }}</td><td>{{ user.status === 'active' ? '正常' : '已停用' }}</td><td>{{ date(user.created_at) }}</td><td><button class="button" :disabled="busy" :aria-label="'查看账户 ' + user.account_normalized" @click="openUser(user)">账户与流水</button></td></tr></tbody></table></div><p v-if="!busy && !users.length">暂无匹配用户。</p><button v-if="cursor" class="button" :disabled="busy" @click="load(false)">加载更多用户</button></section></div>
 <AppDrawer v-model:open="detailOpen" title="目标用户账户与流水"><template v-if="selected"><h3>{{ selected.account_normalized }}</h3><p>{{ selected.id }}</p><p v-if="error" role="alert" class="field-error">{{ error }}</p><dl v-if="account" class="profile-summary"><dt>可用积分</dt><dd data-testid="admin-target-available">{{ account.available }}</dd><dt>冻结积分</dt><dd>{{ account.frozen }}</dd><dt>已消费</dt><dd>{{ account.consumed }}</dd><dt>累计入账</dt><dd>{{ account.credited_total }}</dd></dl><div class="action-row"><button class="button" :disabled="busy" @click="loadAccount(true)">刷新目标账本</button><button class="button primary" :disabled="busy || !!pending" @click="editGrant">发放积分</button></div><p v-if="notice" role="status">{{ notice }}</p><button class="button" :disabled="busy || selected.auth_version===undefined" @click="editStatus">修改账户状态</button><h3>该用户的积分流水</h3><p v-if="!busy && !ledger.length">暂无流水。</p><ul class="admin-records"><li v-for="entry in ledger" :key="entry.ledger_id"><strong>{{ entry.kind }} · {{ entry.amount }} 积分</strong><p>{{ entry.reason }}</p><small>{{ date(entry.created_at) }}</small><details><summary>流水详情</summary><pre>{{ pretty(entry) }}</pre></details></li></ul><button v-if="ledgerCursor" class="button" :disabled="busy" @click="loadAccount(false)">加载更多流水</button></template></AppDrawer>
 <AppDrawer v-model:open="grantOpen" title="发放积分" purpose="edit"><form id="admin-grant" class="form-stack" @submit.prevent="confirmGrant"><p>目标：{{ selected?.account_normalized }}</p><label>发放积分数<input v-model.number="amount" data-initial-focus type="number" min="0" step="1" required :disabled="busy || !!pending"></label><label>发放原因<textarea v-model="reason" maxlength="500" required :disabled="busy || !!pending" /></label><p v-if="error" class="field-error" role="alert">{{ error }}</p></form><template #actions><button class="button primary" form="admin-grant" :disabled="busy || !!pending">确认发放信息</button></template></AppDrawer>
 <AppDialog v-model:open="confirmOpen" title="确认积分发放" purpose="charge"><p>向 {{ selected?.account_normalized }} 发放 {{ amount }} 积分。</p><p>{{ reason }}</p><p>积分发放会记入目标用户账本，不计为支付收入。</p><p v-if="error" role="alert" class="field-error">{{ error }}</p><p v-if="pendingBody">原业务标识 {{ pendingBody.business_key }} 已保存，返回后可继续核对。</p><template #actions><button class="button primary" :disabled="busy" @click="sendGrant">{{ pending ? '同键重试发放' : '确认发放' }}</button></template></AppDialog>
 <AppDrawer v-model:open="configOpen" title="注册赠送配置" purpose="edit"><form id="registration-config" class="form-stack" @submit.prevent="saveConfig"><p>修改仅影响新注册用户。金额须符合已确认的 D-05 政策。</p><p>草稿基于版本：{{ configDraft.expected_version || (creatingConfig ? '空版本（首份配置）' : '尚未读取') }}</p><label>注册赠送积分<input v-model.number="configDraft.amount" type="number" min="0" step="1" required data-initial-focus></label><label>D-05 政策版本<input v-model="configDraft.policy_version" required></label><label>修改原因<textarea v-model="configDraft.reason" maxlength="500" required /></label><p v-if="error" role="alert" class="field-error">{{ error }}</p><button type="button" class="button" :disabled="busy" @click="refreshConfig">查询当前版本（保留草稿）</button><template v-if="!config && configDraft.expected_version === null"><p>读取失败不代表配置不存在。创建首份配置会提交空版本基线，仅在服务端确认尚无配置且通过 D-05 校验时成功。</p><button type="button" class="button" :disabled="busy || creatingConfig" @click="createFirstConfig">创建首份配置</button></template><template v-if="config"><p>当前版本 {{ config.version }} · {{ config.amount }} 积分 · {{ config.policy_version }}</p><button v-if="config.version !== configDraft.expected_version" type="button" class="button" @click="adoptVersion">已核对，采用当前版本继续编辑</button></template></form><template #actions><button class="button primary" form="registration-config" :disabled="busy || !canSaveConfig">保存配置</button></template></AppDrawer>
 <AppDrawer v-model:open="statusOpen" title="修改账户状态" purpose="edit"><form v-if="statusDraft" id="user-status" class="form-stack" @submit.prevent="statusConfirm=true"><p>目标 {{ selected?.account_normalized }} · 草稿账户版本 {{ statusDraft.expected_auth_version }}</p><label>目标状态<select v-model="statusDraft.status"><option value="active">正常</option><option value="disabled">停用</option></select></label><label>已确认 D-09 政策版本<input v-model="statusPolicy" required data-initial-focus></label><p>停用将撤销用户登录，正在处理的任务按已确认政策执行。</p><p v-if="error" class="field-error" role="alert">{{ error }}</p><button type="button" class="button" :disabled="busy" @click="refreshSelected">核对当前账户版本</button><p>当前版本 {{ selected?.auth_version }}</p><button v-if="selected?.auth_version!==undefined && selected.auth_version!==statusDraft.expected_auth_version" type="button" class="button" @click="statusDraft.expected_auth_version=selected.auth_version">已核对，采用当前版本</button></form><template #actions><button class="button primary" form="user-status" :disabled="busy">确认状态修改</button></template></AppDrawer>
 <AppDialog v-model:open="statusConfirm" title="确认账户状态修改" purpose="delete"><p>将 {{ selected?.account_normalized }} 设为{{ statusDraft?.status==='disabled'?'停用':'正常' }}。</p><p v-if="error" class="field-error" role="alert">{{ error }}</p><template #actions><button class="button danger" :disabled="busy" @click="saveStatus">修改账户状态</button></template></AppDialog>
</template>
