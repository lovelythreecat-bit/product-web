<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ warnings: string[] }>()
const visibleWarnings = computed(() => {
  const marker = ': 已交付最佳可用候选 '
  const delivered = new Set(props.warnings.filter(warning => warning.includes(marker))
    .map(warning => warning.slice(0, warning.indexOf(marker))))
  const historical = ': 图片已保留为候选图，未通过审核，不属于成功交付'
  return props.warnings.filter(warning => !warning.endsWith(historical)
    || !delivered.has(warning.slice(0, -historical.length)))
})
</script>

<template>
  <aside v-if="visibleWarnings.length" class="result-warnings" aria-label="待核实提示">
    <strong>待核实提示</strong>
    <ul><li v-for="(warning, index) in visibleWarnings" :key="index">{{ warning }}</li></ul>
  </aside>
</template>

<style scoped>
.result-warnings { margin:0 0 16px; padding:12px 14px; border-left:3px solid var(--color-warning); border-radius:var(--radius-control); background:var(--color-background); color:var(--color-warning); font-size:13px; line-height:1.8; overflow-wrap:anywhere }
.result-warnings strong { font-weight:600 }
.result-warnings ul { margin:4px 0 0; padding-left:20px }
.result-warnings li { white-space:pre-wrap }
</style>
