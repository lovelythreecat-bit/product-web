<script setup lang="ts">
import { ElTable, ElTableColumn } from 'element-plus/es/components/table/index'
import UiSelect from '../../components/ui/UiSelect.vue'
import UiInput from '../../components/ui/UiInput.vue'
import UiButton from '../../components/ui/UiButton.vue'
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as api from '../../api/admin'
import type { Schema } from '../../types/api'
import AppDrawer from '../../components/AppDrawer.vue'
import UiPagination from '../../components/ui/UiPagination.vue'
import { useAdminRequest, date, taskStates, settlements } from './shared'
import { investigationStates, diagnosticCodes } from './display'
import { useUserAccounts } from './userAccounts'
const {busy,error,run,current}=useAdminRequest()
const { users: userAccounts, loading: accountsLoading, error: accountsError, load: loadUserAccounts, accountName } = useUserAccounts()
const tasks=ref<Schema<'TaskDiagnosticView'>[]>([]), state=ref(''), user=ref('')
const page = ref(1), total = ref(0)
const keyword=ref(''),agentFilter=ref(''),agents=ref<Schema<'AgentVersion'>[]>([])
const route=useRoute()
user.value=typeof route?.query.user_id==='string'?route.query.user_id:''
const detail=ref<Schema<'TaskDiagnosticView'>|null>(null), detailOpen=ref(false)
let applied={state:'',user:'',q:'',agent:''}
function load(target=1, reset=true) {
 const filter=reset?{state:state.value,user:user.value.trim(),q:keyword.value.trim(),agent:agentFilter.value}:applied
 return run(()=>api.listTasks(undefined,filter.state||undefined,filter.user||undefined,filter.q||undefined,filter.agent||undefined,target),result=>{
  applied=filter; tasks.value=result.items; page.value=result.page??target;total.value=result.total
 })
}
function loadAgents(){void api.listAgents().then(result=>{if(current())agents.value=result}).catch(()=>{if(current())error.value='暂时无法读取 Agent 列表，请刷新后重试。'})}
function agentName(id:string){return agents.value.find(agent=>agent.agent_id===id)?.name || id}
watch(()=>route?.query.user_id,value=>{user.value=typeof value==='string'?value:'';void load()})

function show(id:string){detail.value=null;detailOpen.value=true;return run(()=>api.diagnostics(id),d=>{detail.value=d})}
onMounted(() => { void load(); void loadUserAccounts(); loadAgents() })
const TColumn = ElTableColumn<Schema<'TaskDiagnosticView'>>
</script>
<template><div class="admin-page admin-list-page"><p v-if="error" class="field-error" role="alert">{{ error }}</p>
<section class="panel admin-list-panel" aria-label="任务诊断"><h2>任务诊断</h2><form class="admin-filters" @submit.prevent="load()"><label>任务状态<UiSelect v-model="state"><option value="">全部</option><option v-for="(label,key) in taskStates" :key="key" :value="key">{{ label }}</option></UiSelect></label><label for="admin-task-keyword">任务 / 用户 / 账号<UiInput id="admin-task-keyword" v-model="keyword" placeholder="输入关键词" /></label><label for="admin-task-agent">Agent<UiSelect id="admin-task-agent" v-model="agentFilter"><option value="">全部</option><option v-for="agent in agents" :key="agent.agent_id" :value="agent.agent_id">{{ agent.name }}</option></UiSelect></label><label>用户账号<UiSelect v-model="user" :disabled="accountsLoading"><option value="">全部</option><option v-if="user && !userAccounts.some(account => account.id===user)" :value="user">账号未提供</option><option v-for="account in userAccounts" :key="account.id" :value="account.id">{{ account.account_normalized }}</option></UiSelect></label><p v-if="accountsError" class="field-error" role="alert">{{ accountsError }}</p><UiButton class="button" :disabled="busy">查询任务</UiButton><UiButton type="button" class="button" :disabled="busy" @click="state='';user='';keyword='';agentFilter='';load()">清空</UiButton></form><div class="admin-table admin-list-table" tabindex="0" role="region" aria-label="任务列表，可横向滚动"><ElTable height="100%" :data="tasks" row-key="id" class="ui-data-table" :empty-text="busy ? '正在读取任务…' : '暂无匹配任务'" border><TColumn  :min-width="140"><template #header>用户</template><template #default="{ row: t }">{{ t.account || accountName(t.user_id) }}</template></TColumn><TColumn  :min-width="140"><template #header>状态</template><template #default="{ row: t }">{{ taskStates[t.state] }}</template></TColumn><TColumn  :min-width="140"><template #header>结算</template><template #default="{ row: t }">{{ settlements[t.settlement_state] }}</template></TColumn><TColumn  :min-width="140"><template #header>Agent / 耗时</template><template #default="{ row: t }">{{ agentName(t.agent_id) }} · {{ t.elapsed_seconds.toFixed(0) }} 秒</template></TColumn><TColumn  :min-width="140"><template #header>固定费用</template><template #default="{ row: t }">{{ t.fixed_credits == null ? '费用未记录' : t.fixed_credits + ' 积分' }}</template></TColumn><TColumn  :min-width="140"><template #header>诊断</template><template #default="{ row: t }">{{ t.diagnostic_code ? (diagnosticCodes[t.diagnostic_code] || t.diagnostic_code) : '无异常' }}</template></TColumn><TColumn  :min-width="140"><template #header>操作</template><template #default="{ row: t }"><UiButton class="button" :disabled="busy" @click="show(t.id)">查看诊断</UiButton></template></TColumn></ElTable></div><UiPagination class="admin-pagination" :page="page" :total="total" :disabled="busy" @change="load($event,false)" /></section></div>
<AppDrawer v-model:open="detailOpen" title="原任务诊断" :show-footer="false"><p v-if="error" class="field-error" role="alert">{{ error }}</p><template v-if="detail"><dl class="detail-list"><dt>任务标识</dt><dd>{{ detail.id }}</dd><dt>状态 / 结算</dt><dd>{{ taskStates[detail.state] }} / {{ settlements[detail.settlement_state] }}</dd><dt>Agent 版本</dt><dd>{{ detail.agent_id }} / {{ detail.agent_version }}</dd><dt>必要错误信息</dt><dd>{{ detail.diagnostic_code ? (diagnosticCodes[detail.diagnostic_code] || detail.diagnostic_code) : '无异常' }}</dd><dt>核查</dt><dd>{{ detail.investigation_status ? (investigationStates[detail.investigation_status] || detail.investigation_status) : '尚未登记' }} / {{ detail.investigation_owner ? accountName(detail.investigation_owner) : '未分配' }}</dd><dt>累计耗时</dt><dd>{{ detail.elapsed_seconds.toFixed(0) }} 秒</dd><dt>核查截止时间</dt><dd>{{ detail.investigation_deadline?date(detail.investigation_deadline):'未设定' }}</dd><dt>创建时间</dt><dd>{{ date(detail.created_at) }}</dd><dt>更新时间</dt><dd>{{ detail.updated_at?date(detail.updated_at):'未记录' }}</dd><dt>账号 / 会话</dt><dd>{{ detail.account || '未记录' }} / {{ detail.conversation_id || '未记录' }}</dd><dt>固定费用</dt><dd>{{ detail.fixed_credits == null ? '未记录' : detail.fixed_credits + ' 积分' }}</dd><dt>计价记录</dt><dd>{{ detail.price_version || '未记录' }}</dd><dt>外部提交标识</dt><dd>{{ detail.external_submission_id || '未记录' }}</dd><dt>上游任务标识</dt><dd>{{ detail.upstream_id || '未记录' }}</dd><dt>关联成果编号</dt><dd>{{ detail.work_ids === undefined ? '关联成果未提供' : detail.work_ids.length ? detail.work_ids.join('、') : '无' }}</dd></dl><h3>任务时间线</h3><ol class="admin-records"><li v-for="event in (detail.timeline ?? [])" :key="event.state_version"><strong>版本 {{ event.state_version }} · {{ event.from_state?taskStates[event.from_state]:'初始' }} → {{ taskStates[event.to_state] }}</strong><small>{{ date(event.created_at) }}</small></li></ol><p v-if="detail.timeline === undefined">响应尚未提供状态记录。</p><p v-else-if="!detail.timeline.length">暂无状态记录。</p></template></AppDrawer>
</template>
