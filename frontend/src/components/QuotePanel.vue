<script setup lang="ts">
import type { Schema } from '../types/api'
defineProps<{ quote: Schema<'Quote'> | null; loading?: boolean }>()
</script>
<template><div class="quote-panel" aria-live="polite"><span>本次费用</span><p v-if="loading" class="quote-placeholder">报价中…</p><p v-else-if="quote" class="quote-value"><strong>{{ quote.credits }}</strong><span>积分</span></p><p v-else class="quote-placeholder">—</p></div></template>
<style scoped>
.quote-panel { display:flex; align-items:center; justify-content:space-between; gap:12px }
.quote-panel>span { font-size:13px }
.quote-value { display:flex; align-items:baseline; gap:6px; font-variant-numeric:tabular-nums; line-height:1.2; margin:0 }
.quote-value strong { font-size:28px; font-weight:650 }
.quote-value>span { font-size:13px; font-weight:600 }
.quote-placeholder { margin:0; min-height:34px; display:flex; align-items:center; font-size:13px; color:var(--color-muted) }
</style>
