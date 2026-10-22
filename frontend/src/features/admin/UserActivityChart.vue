<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { init, use, type EChartsCoreOption } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, SVGRenderer])
const props = defineProps<{ days: { date: string; registered_count?: number; active_user_count?: number }[] }>()
const element = ref<HTMLDivElement | null>(null)
const series = [
  { name: '注册用户', key: 'registered_count', color: '#a94e32', symbol: 'circle', line: 'solid' },
  { name: '活跃用户', key: 'active_user_count', color: '#706259', symbol: 'rect', line: 'dashed' },
] as const
const description = computed(() => `用户每日趋势；${props.days.map(day => `${day.date}：注册 ${day.registered_count ?? '未提供'} 人，活跃 ${day.active_user_count ?? '未提供'} 人`).join('；')}`)
const option = computed<EChartsCoreOption>(() => ({
  animation: false,
  textStyle: { fontFamily: 'inherit' },
  grid: { top: 16, right: 12, bottom: 26, left: 36 },
  tooltip: { trigger: 'axis', confine: true, backgroundColor: '#fffdfa', borderColor: '#e7d9ca', valueFormatter: (value: unknown) => typeof value === 'number' ? `${value.toLocaleString('zh-CN')} 人` : '未提供' },
  xAxis: { type: 'category', data: props.days.map(day => day.date), boundaryGap: false, axisTick: { show: false }, axisLine: { lineStyle: { color: '#dccfc2' } }, axisLabel: { color: '#706259', hideOverlap: true, formatter: (date: string) => date.slice(5).replace('-', '/') } },
  yAxis: { type: 'value', min: 0, minInterval: 1, max: props.days.every(day => !day.registered_count && !day.active_user_count) ? 1 : undefined, axisLabel: { color: '#706259' }, splitLine: { lineStyle: { color: '#e9dfd5' } } },
  series: series.map(item => ({ name: item.name, type: 'line', data: props.days.map(day => day[item.key] ?? null), symbol: item.symbol, symbolSize: 5, itemStyle: { color: item.color }, lineStyle: { color: item.color, type: item.line, width: 2 }, connectNulls: false })),
}))
watch(element, (target, _previous, cleanup) => {
  if (!target) return
  const chart = init(target, undefined, { renderer: 'svg' })
  chart.setOption(option.value)
  const stop = watch(option, value => chart.setOption(value, { notMerge: true }))
  const resize = () => chart.resize()
  const observer = typeof ResizeObserver === 'undefined' ? undefined : new ResizeObserver(resize)
  observer?.observe(target)
  window.addEventListener('resize', resize)
  cleanup(() => { stop(); observer?.disconnect(); window.removeEventListener('resize', resize); chart.dispose() })
}, { flush: 'post' })
</script>

<template>
  <div class="user-trend-legend" aria-label="用户趋势图例"><span>注册用户</span><span>活跃用户</span></div>
  <div ref="element" class="user-trend-chart" role="img" :aria-label="description" />
</template>

<style scoped>
.user-trend-legend { display:flex; gap:16px; color:var(--color-muted); font-size:12px; }
.user-trend-legend span { display:flex; align-items:center; gap:6px; }
.user-trend-legend span::before { content:''; width:16px; border-top:2px solid var(--color-primary); }
.user-trend-legend span + span::before { border-color:var(--color-muted); border-top-style:dashed; }
.user-trend-chart { width:100%; height:184px; overflow:hidden; }
.user-trend-chart :deep(svg) { width:100%; height:100%; }
</style>
