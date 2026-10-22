<script setup lang="ts">
import { computed } from 'vue'
import { fieldLabels, displayValue, isUserIdentityField } from './display'
const props = defineProps<{ value: Record<string,unknown> }>()
const visibleFields = computed(() => Object.fromEntries(Object.entries(props.value).filter(([key]) => !isUserIdentityField(key))))
</script>
<template><dl class="record-fields"><template v-for="(item,key) in visibleFields" :key="key"><dt>{{ fieldLabels[key] || key }}</dt><dd><RecordFields v-if="item && typeof item==='object' && !Array.isArray(item)" :value="item as Record<string,unknown>" /><ul v-else-if="Array.isArray(item)"><li v-for="(entry,index) in item" :key="index"><RecordFields v-if="entry && typeof entry==='object'" :value="entry as Record<string,unknown>" /><template v-else>{{ displayValue(entry) }}</template></li></ul><template v-else>{{ displayValue(item) }}</template></dd></template></dl></template>
<style scoped>.record-fields{display:grid;grid-template-columns:minmax(100px,.4fr) minmax(0,1fr);gap:12px 20px}.record-fields dt{color:var(--text-muted,#706259)}.record-fields dd{margin:0;overflow-wrap:anywhere;white-space:pre-wrap}.record-fields .record-fields{grid-template-columns:minmax(80px,.4fr) minmax(0,1fr);margin:0}@media(max-width:520px){.record-fields,.record-fields .record-fields{grid-template-columns:minmax(0,1fr);gap:6px}.record-fields dd{margin-bottom:12px}}</style>
