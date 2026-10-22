<script setup lang="ts">
import { ElTable, ElTableColumn } from 'element-plus/es/components/table/index'
import UiSelect from '../../components/ui/UiSelect.vue'
import UiInput from '../../components/ui/UiInput.vue'
import UiButton from '../../components/ui/UiButton.vue'
import { onMounted, ref } from 'vue'
import * as api from '../../api/admin'
import type { Schema } from '../../types/api'
import AppDrawer from '../../components/AppDrawer.vue'
import { useAdminRequest, date } from './shared'
import RecordFields from './RecordFields.vue'
import UiPagination from '../../components/ui/UiPagination.vue'
import { auditActions } from './display'
import { useUserAccounts } from './userAccounts'
const {busy,error,run}=useAdminRequest()
const { load: loadUserAccounts, accountName, error: accountsError } = useUserAccounts()
function objectName(row: Schema<'AuditView'>) { return row.action==='account_status' ? accountName(row.object_id) : row.object_id }
const rows=ref<Schema<'AuditView'>[]>([]),action=ref(''),customAction=ref(''),actor=ref(''),object=ref(''),open=ref(false),detail=ref<Schema<'AuditView'>|null>(null)
const keyword=ref('')
const page = ref(1), total = ref(0)
let applied={action:'',actor:'',object:'',q:''}
function load(target=1, reset=true) {
 const filter=reset?{action:action.value==='__custom'?customAction.value:action.value,actor:actor.value,object:object.value,q:keyword.value.trim()}:applied
 return run(()=>api.listAudit(undefined,filter.action||undefined,filter.actor||undefined,filter.object||undefined,filter.q||undefined,target),result=>{
  applied=filter;rows.value=result.items;page.value=result.page??target;total.value=result.total
 })
}
onMounted(() => { void load(); void loadUserAccounts() })
const RowColumn = ElTableColumn<Schema<'AuditView'>>
</script>
<template><div class="admin-page admin-list-page"><section class="panel admin-list-panel" aria-label="操作日志列表"><form class="admin-filters" @submit.prevent="load()"><label>操作类型<UiSelect v-model="action"><option value="">全部</option><option v-for="(label,key) in auditActions" :key="key" :value="key">{{ label }}</option><option value="__custom">其他操作类型</option></UiSelect></label><label v-if="action==='__custom'">操作类型标识<UiInput v-model="customAction" placeholder="填写记录中的完整类型标识" /></label><label for="admin-audit-keyword">对象 / 操作人 / 原因<UiInput id="admin-audit-keyword" v-model="keyword" placeholder="输入关键词" /></label><UiButton class="button" :disabled="busy">查询审计</UiButton><UiButton type="button" class="button" :disabled="busy" @click="keyword='';action='';customAction='';actor='';object='';load()">清空</UiButton></form><p v-if="error" role="alert" class="field-error">{{ error }}</p><p v-if="accountsError" role="alert" class="field-error">{{ accountsError }}</p><div class="admin-table admin-list-table" tabindex="0" role="region" aria-label="操作日志，可横向滚动"><ElTable height="100%" :data="rows" row-key="id" class="ui-data-table" :empty-text="busy ? '正在读取日志…' : '暂无匹配的审计记录'" border><RowColumn  :min-width="140"><template #header>时间</template><template #default="{ row: row }">{{ date(row.created_at) }}</template></RowColumn><RowColumn  :min-width="140"><template #header>操作</template><template #default="{ row: row }">{{ auditActions[row.action] || row.action }}</template></RowColumn><RowColumn  :min-width="140"><template #header>操作人</template><template #default="{ row: row }">{{ row.actor_id ? accountName(row.actor_id) : '系统' }}</template></RowColumn><RowColumn  :min-width="140"><template #header>原因</template><template #default="{ row: row }">{{ row.reason }}</template></RowColumn><RowColumn  :min-width="140"><template #header>详情</template><template #default="{ row: row }"><UiButton class="button" @click="detail=row;open=true">查看详情</UiButton></template></RowColumn></ElTable></div><UiPagination class="admin-pagination" :page="page" :total="total" :disabled="busy" @change="load($event,false)" /></section></div><AppDrawer v-model:open="open" title="操作日志详情"><template v-if="detail"><dl class="detail-list"><dt>操作人</dt><dd>{{ detail.actor_id ? accountName(detail.actor_id) : '系统' }}</dd><dt>对象</dt><dd>{{ objectName(detail) }}</dd><dt>操作</dt><dd>{{ auditActions[detail.action] || detail.action }}</dd><dt>原因</dt><dd>{{ detail.reason }}</dd><dt>时间</dt><dd>{{ date(detail.created_at) }}</dd></dl><h3>变更记录</h3><RecordFields :value="detail.changes" /></template></AppDrawer></template>
