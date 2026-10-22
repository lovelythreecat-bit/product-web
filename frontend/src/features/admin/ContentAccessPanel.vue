<script setup lang="ts">
import UiButton from '../../components/ui/UiButton.vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import UiInput from '../../components/ui/UiInput.vue'
import { computed, ref, watch } from 'vue'
import * as api from '../../api/admin'
import type { Schema } from '../../types/api'
import AppDrawer from '../../components/AppDrawer.vue'
import AppDialog from '../../components/AppDialog.vue'
import { session } from '../auth/session'
import { useAdminRequest, date, pretty } from './shared'
import { resourceTypes } from './display'
import { useUserAccounts } from './userAccounts'
const {busy,error,run}=useAdminRequest()
const { users: userAccounts, loading: accountsLoading, error: accountsError, load: loadUserAccounts, accountName } = useUserAccounts()
const authorizedAdminAccounts = computed(() => userAccounts.value.filter(account => account.role==='admin' && account.id!==session.profile.value?.user_id))
const open=ref(false), grantOpen=ref(false), revokeOpen=ref(false), contentOpen=ref(false), grants=ref<Schema<'ContentGrantView'>[]>([]), cursor=ref<string|null>(null)
const actor=ref(''), target=ref(''), resource=ref(''), resourceType=ref<Schema<'ContentScope'>['resource_type']>('task'), reason=ref(''), expires=ref('')
const readType=ref<Schema<'ContentScope'>['resource_type']>('task'), readId=ref(''), readReason=ref(''), content=ref<Schema<'AuditedContent'>|null>(null), revokeTarget=ref<Schema<'ContentGrantView'>|null>(null), revokeReason=ref('')
const types:Schema<'ContentScope'>['resource_type'][]=['task','message','work','file','material','conversation','product_version']
function load(reset=true){return run(()=>api.listContentGrants(reset?undefined:cursor.value??undefined),p=>{grants.value=reset?p.items:[...grants.value,...p.items];cursor.value=p.next_cursor})}
function show(){open.value=true;void load();void loadUserAccounts()}
async function grant(){if(actor.value===session.profile.value?.user_id){error.value='不能为自己授予内容访问权限。';return} if(await run(()=>api.createContentGrant({actor_id:actor.value,scope:{user_id:target.value,resource_id:resource.value,resource_type:resourceType.value},reason:reason.value,expires_at:new Date(expires.value).toISOString()}),()=>{grantOpen.value=false}))await load()}
function requestRevoke(g:Schema<'ContentGrantView'>){revokeTarget.value=g;revokeReason.value='';revokeOpen.value=true}
async function revoke(){if(!revokeTarget.value)return;if(await run(()=>api.revokeContentGrant(revokeTarget.value!.id,revokeReason.value),()=>{revokeOpen.value=false;content.value=null;contentOpen.value=false}))await load()}
function read(){content.value=null;return run(()=>api.readContent(readType.value,readId.value,readReason.value),r=>{content.value=r;contentOpen.value=true})}
watch(contentOpen,v=>{if(!v)content.value=null})
</script>
<template><section class="panel"><div class="section-heading"><h2>独立内容授权</h2><UiButton class="button" @click="show">查看授权与访问入口</UiButton></div><p>普通管理员权限不包含用户正文。访问须有指定对象授权，并填写本次原因。</p></section>
<AppDrawer v-model:open="open" title="独立内容授权与访问"><p>批准资格由服务端单独校验，不能自行授权。生产批准来源尚未确认，默认关闭；测试环境也仅限显式配置的批准者。</p><p v-if="error" class="field-error" role="alert">{{ error }}</p><div class="action-row"><UiButton class="button" :disabled="busy" @click="load()">刷新授权</UiButton><UiButton class="button" :disabled="busy" @click="grantOpen=true">提交指定对象授权</UiButton></div><ul class="admin-records"><li v-for="g in grants" :key="g.id"><strong>{{ resourceTypes[g.resource_type] }} · {{ g.resource_id }}</strong><p>访问者 {{ accountName(g.actor_id) }} · 批准者 {{ accountName(g.approver_id) }}</p><p>{{ g.revoked_at?'已撤销':new Date(g.expires_at).getTime()<=Date.now()?'已过期':'有效至 '+date(g.expires_at) }}</p><p>{{ g.reason }}</p><UiButton class="button" :disabled="busy || !!g.revoked_at" @click="requestRevoke(g)">撤销授权</UiButton></li></ul><p v-if="!busy && !grants.length">暂无可见授权。</p><UiButton v-if="cursor" class="button" :disabled="busy" @click="load(false)">加载更多授权</UiButton><h3>读取获授权内容</h3><form class="form-stack" @submit.prevent="read"><label>内容类型<UiSelect v-model="readType"><option v-for="t in types" :key="t" :value="t">{{ resourceTypes[t] }}</option></UiSelect></label><label>内容对象标识<UiInput v-model="readId" required /></label><label>本次访问原因<UiInput type="textarea" v-model="readReason" required maxlength="500" /></label><UiButton class="button primary" :disabled="busy">记录原因并读取内容</UiButton></form></AppDrawer>
<AppDrawer v-model:open="grantOpen" title="提交指定对象内容授权" purpose="edit"><form id="content-grant" class="form-stack" @submit.prevent="grant"><p>仅独立批准者可提交，普通管理员角色不代表批准资格。</p><label>被授权管理员账号<UiSelect v-model="actor" required data-initial-focus :disabled="accountsLoading"><option value="">请选择管理员</option><option v-for="account in authorizedAdminAccounts" :key="account.id" :value="account.id">{{ account.account_normalized }}</option></UiSelect></label><label>内容所属用户账号<UiSelect v-model="target" required :disabled="accountsLoading"><option value="">请选择用户</option><option v-for="account in userAccounts" :key="account.id" :value="account.id">{{ account.account_normalized }}</option></UiSelect></label><p v-if="accountsError" class="field-error" role="alert">{{ accountsError }}</p><label>授权对象类型<UiSelect v-model="resourceType"><option v-for="t in types" :key="t" :value="t">{{ resourceTypes[t] }}</option></UiSelect></label><label>授权对象标识<UiInput v-model="resource" required /></label><label>授权到期时间<UiInput v-model="expires" type="datetime-local" required /></label><label>授权原因<UiInput type="textarea" v-model="reason" required maxlength="500" /></label><p v-if="error" class="field-error" role="alert">{{ error }}</p></form><template #actions><UiButton class="button primary" form="content-grant" :disabled="busy || actor===session.profile.value?.user_id">提交授权</UiButton></template></AppDrawer>
<AppDialog v-model:open="revokeOpen" title="确认撤销内容授权" purpose="delete"><form id="revoke-grant" class="form-stack" @submit.prevent="revoke"><p>{{ revokeTarget?resourceTypes[revokeTarget.resource_type]:'' }} · {{ revokeTarget?.resource_id }}</p><label>撤销原因<UiInput type="textarea" v-model="revokeReason" required maxlength="500" /></label><p v-if="error" class="field-error" role="alert">{{ error }}</p></form><template #actions><UiButton class="button danger" form="revoke-grant" :disabled="busy">撤销授权</UiButton></template></AppDialog>
<AppDrawer v-model:open="contentOpen" title="获授权内容"><template v-if="content"><p>本次读取已记录审计 {{ content.audit_id }}，授权 {{ content.grant_id }}。</p><pre>{{ pretty(content.content) }}</pre><p>关闭后清除本次正文；再次读取重新校验权限。</p></template></AppDrawer></template>
