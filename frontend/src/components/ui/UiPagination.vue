<script setup lang="ts">
import { ElPagination } from 'element-plus/es/components/pagination/index'

const props = withDefaults(defineProps<{
  page: number
  total: number
  pageSize?: number
  disabled?: boolean
  label?: string
}>(), { pageSize: 20, disabled: false, label: '列表分页' })
const emit = defineEmits<{ change: [page: number] }>()
function change(page: number) {
  if (!props.disabled && page !== props.page) emit('change', page)
}
</script>

<template>
  <nav class="ui-pagination" :aria-label="label" :aria-busy="disabled">
    <ElPagination
      :current-page="page"
      :page-size="pageSize"
      :total="total"
      :pager-count="5"
      layout="total, prev, pager, next, jumper"
      :disabled="disabled"
      @current-change="change"
    />
  </nav>
</template>

<style scoped>
.ui-pagination { display:flex; flex:none; justify-content:flex-end; min-width:0; width:100%; padding-top:16px; text-align:left; font-variant-numeric:tabular-nums; }
.ui-pagination :deep(.el-pagination) { flex-wrap:wrap; justify-content:flex-end; gap:8px; }
.ui-pagination :deep(.el-pagination > *) { margin:0; }
@media(max-width:700px), (pointer:coarse) {
  .ui-pagination :deep(.el-pagination) { --el-pagination-button-height:44px; --el-pagination-button-width:44px; }
  .ui-pagination :deep(.el-pagination__editor.el-input) { --el-input-height:44px; }
}
@media(max-width:700px) {
  .ui-pagination { justify-content:flex-start; padding-top:12px; }
  .ui-pagination :deep(.el-pagination) { --el-pagination-button-width:36px; justify-content:flex-start; column-gap:4px; }
  .ui-pagination :deep(.el-pagination__total) { flex-basis:100%; }
  .ui-pagination :deep(.el-pagination__jump) { flex-basis:100%; justify-content:flex-start; }
}
@media(max-width:360px) {
  .ui-pagination :deep(.el-pagination) { --el-pagination-button-width:32px; column-gap:0; }
}
</style>
