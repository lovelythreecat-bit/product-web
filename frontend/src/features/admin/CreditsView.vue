<script setup lang="ts">
import { ElTable, ElTableColumn } from 'element-plus/es/components/table/index'
import { onMounted, ref } from 'vue'
import UiInput from '../../components/ui/UiInput.vue'
import UiButton from '../../components/ui/UiButton.vue'
import AppDrawer from '../../components/AppDrawer.vue'
import * as api from '../../api/admin'
import type { Schema } from '../../types/api'
import { useAdminRequest, date } from './shared'
import { ledgerKinds } from './display'
import { useUserAccounts } from './userAccounts'
import RecordFields from './RecordFields.vue'
import UiPagination from '../../components/ui/UiPagination.vue'

const { busy, error, run } = useAdminRequest()
const { accountName, load: loadUserAccounts, error: accountsError } = useUserAccounts()
const rows = ref<Schema<'AdminLedgerEntryView'>[]>([])
const keyword = ref('')
const detail = ref<Schema<'AdminLedgerEntryView'> | null>(null)
const detailOpen = ref(false)
const page = ref(1), total = ref(0)
let appliedKeyword = ''
function load(target=1, reset=true) {
  const query = reset ? keyword.value.trim() : appliedKeyword
  return run(() => api.listAdminLedger(undefined, query || undefined, target), result => {
    appliedKeyword = query
    rows.value = result.items
    page.value = result.page ?? target; total.value = result.total
  })
}
onMounted(() => { void load(); void loadUserAccounts() })
const EntryColumn = ElTableColumn<Schema<'AdminLedgerEntryView'>>
</script>
<template>
  <div class="admin-page admin-list-page">

    <section class="panel admin-list-panel" aria-label="积分流水列表">
      <form id="platform-ledger-query" class="admin-filters" @submit.prevent="load()">
        <label for="admin-ledger-keyword">账户 / 原因<UiInput id="admin-ledger-keyword" v-model="keyword" placeholder="输入关键词" /></label>
        <UiButton class="button" :disabled="busy">查询流水</UiButton>
        <UiButton type="button" class="button" :disabled="busy" @click="keyword='';load()">清空</UiButton>
      </form>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
      <p v-if="accountsError" class="field-error" role="alert">{{ accountsError }}</p>
      <div class="admin-table admin-list-table" tabindex="0" role="region" aria-label="平台积分流水，可横向滚动">
        <ElTable :data="rows" height="100%" row-key="ledger_id" class="ui-data-table" :empty-text="busy ? '正在读取积分流水…' : '暂无匹配流水'" border>
          <EntryColumn :min-width="170"><template #header>时间</template><template #default="{ row: entry }">{{ date(entry.created_at) }}</template></EntryColumn>
          <EntryColumn :min-width="160"><template #header>接收账户</template><template #default="{ row: entry }">{{ entry.account }}</template></EntryColumn>
          <EntryColumn :min-width="120"><template #header>类型</template><template #default="{ row: entry }">{{ ledgerKinds[entry.kind] || entry.kind }}</template></EntryColumn>
          <EntryColumn :min-width="100" align="right"><template #header>积分数量</template><template #default="{ row: entry }">{{ entry.amount }}</template></EntryColumn>
          <EntryColumn :min-width="130" align="right"><template #header>变更前可用积分</template><template #default="{ row: entry }">{{ entry.balances_before.available }}</template></EntryColumn>
          <EntryColumn :min-width="130" align="right"><template #header>变更后可用积分</template><template #default="{ row: entry }">{{ entry.balances_after.available }}</template></EntryColumn>
          <EntryColumn :min-width="180"><template #header>关联任务</template><template #default="{ row: entry }">{{ entry.task_name || (entry.task_id ? '未命名任务' : '无') }}</template></EntryColumn>
          <EntryColumn :min-width="140"><template #header>操作人</template><template #default="{ row: entry }">{{ entry.operator ? accountName(entry.operator) : '系统' }}</template></EntryColumn>
          <EntryColumn :min-width="120"><template #header>操作</template><template #default="{ row: entry }"><UiButton type="button" class="button" @click="detail=entry;detailOpen=true">流水详情</UiButton></template></EntryColumn>
        </ElTable>
      </div>
      <UiPagination class="admin-pagination" :page="page" :total="total" :disabled="busy" @change="load($event,false)" />
    </section>
  </div>
  <AppDrawer v-model:open="detailOpen" title="积分流水详情"><RecordFields v-if="detail" :value="detail" /></AppDrawer>
</template>
<style scoped>
.admin-page .admin-table :deep(.el-table__cell) {padding:10px 0}
.admin-page .admin-table :deep(th .cell) {white-space:nowrap;overflow-wrap:normal}
</style>
