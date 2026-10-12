<script setup lang="ts">
import type { Schema } from '../types/api'
defineProps<{ quote: Schema<'Quote'> | null; loading?: boolean }>()
</script>
<template><div class="quote-panel" aria-live="polite"><span>本次费用</span><p v-if="loading">正在核对当前报价…</p><p v-else-if="quote"><strong>{{ quote.credits }}</strong> 积分</p><p v-else>完善资料与设置后显示报价</p><small>确认后冻结积分，完整成功后扣除</small></div></template>
