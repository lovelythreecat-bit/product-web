<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { init, use, type EChartsCoreOption, type EChartsType } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'

import UiButton from '../../components/ui/UiButton.vue'
import UserActivityChart from './UserActivityChart.vue'
import * as api from '../../api/admin'
import type { Schema } from '../../types/api'
import { taskStates, useAdminRequest } from './shared'

use([BarChart, GridComponent, TooltipComponent, SVGRenderer])

type AgentUsage = Schema<'AgentUsageView'>
type Dashboard = Schema<'StatisticsView'>
const { busy, error, run } = useAdminRequest()
const stats = ref<Dashboard | null>(null)
const agents = ref<Schema<'AgentVersion'>[]>([])
const namesUnavailable = ref(false)
const updatedAt = ref('')
const metric = ref<'task_count' | 'credits_consumed'>('task_count')
const chartElement = ref<HTMLDivElement | null>(null)
let chart: EChartsType | undefined
watch(chartElement, (element, _previous, onCleanup) => {
  if (!element) return
  chart = init(element, undefined, { renderer: 'svg' })
  chart.setOption(chartOption.value)
  const resize = () => chart?.resize()
  const observer = typeof ResizeObserver === 'undefined' ? undefined : new ResizeObserver(resize)
  observer?.observe(element)
  window.addEventListener('resize', resize)
  onCleanup(() => {
    observer?.disconnect()
    window.removeEventListener('resize', resize)
    chart?.dispose()
    chart = undefined
  })
}, { flush: 'post' })
const number = (value: number | null | undefined) => value == null ? '未提供' : value.toLocaleString('zh-CN')
const rate = (value: number | null | undefined) => value === null ? '暂无终态样本' : value === undefined ? '未提供' : (value * 100).toFixed(1) + '%'
const kindName: Record<string, string> = { copy: '文案', text: '文本', image: '图片', video: '视频' }

function load() {
  return run(async () => {
    const [value, currentAgents] = await Promise.all([
      api.statistics(),
      api.listAgents().then(value => ({ value, failed: false })).catch(() => ({ value: [], failed: true })),
    ])
    return { value, currentAgents }
  }, ({ value, currentAgents }) => {
    stats.value = value
    agents.value = currentAgents.value
    namesUnavailable.value = currentAgents.failed
    updatedAt.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })
}

function emptyUsage(agent_id: string): AgentUsage {
  return {
    agent_id, task_count: 0, succeeded_count: 0, failed_count: 0,
    manually_closed_count: 0, terminal_count: 0, success_rate: null,
    unsettled_count: 0, credits_consumed: 0, credits_frozen: 0, credits_released: 0,
  }
}
const agentRows = computed(() => {
  const rows = new Map<string, { id: string; name: string; kind: string; usage: AgentUsage | undefined }>()
  for (const agent of agents.value) {
    if (!rows.has(agent.agent_id)) rows.set(agent.agent_id, {
      id: agent.agent_id, name: agent.name, kind: kindName[agent.kind] || agent.kind,
      usage: stats.value?.by_agent === undefined ? undefined : emptyUsage(agent.agent_id),
    })
  }
  for (const usage of stats.value?.by_agent || []) {
    const existing = rows.get(usage.agent_id)
    rows.set(usage.agent_id, {
      id: usage.agent_id, name: existing?.name || '未命名 Agent',
      kind: existing?.kind || '', usage,
    })
  }
  return [...rows.values()]
})
const stateRows = computed(() => Object.entries(stats.value?.state_counts || {}).map(([state, count]) => ({
  state, name: taskStates[state] || state, count,
})))
const segments = [
  { key: 'succeeded_count', name: '成功', color: '#a94e32' },
  { key: 'failed_count', name: '失败', color: '#d28c63' },
  { key: 'manually_closed_count', name: '人工关闭', color: '#94735a' },
] as const
function share(value: number | undefined, total: number | undefined) {
  return total && value ? Math.min(100, value / total * 100) : 0
}
function activeCount(row: AgentUsage) {
  return row.terminal_count === undefined ? undefined : row.task_count - row.terminal_count
}
const trend = computed(() => stats.value?.daily_trend || [])
const today = computed(() => trend.value.at(-1))
const userTrendAvailable = computed(() => trend.value.some(day => day.registered_count !== undefined || day.active_user_count !== undefined))
const trendTitle = computed(() => metric.value === 'task_count' ? '任务量' : '消费积分')
const trendTotal = computed(() => trend.value.reduce((total, day) => total + day[metric.value], 0))
const trendDescription = computed(() => `${trendTitle.value}日趋势；${trend.value.map(day => `${day.date}：${number(day[metric.value])}${metric.value === 'task_count' ? '次' : '积分'}`).join('；')}`)
const chartOption = computed<EChartsCoreOption>(() => ({
  animation: false,
  color: [metric.value === 'task_count' ? '#a94e32' : '#a87035'],
  textStyle: { fontFamily: 'inherit', color: '#6e5b50' },
  grid: { top: 16, right: 12, bottom: 26, left: 44 },
  tooltip: {
    trigger: 'axis', confine: true, renderMode: 'html', axisPointer: { type: 'shadow' },
    backgroundColor: '#fffdfa', borderColor: '#dccfc2', textStyle: { color: '#322823', fontSize: 13 },
    valueFormatter: (value: unknown) => `${number(typeof value === 'number' ? value : undefined)} ${metric.value === 'task_count' ? '次' : '积分'}`,
  },
  xAxis: {
    type: 'category', data: trend.value.map(day => day.date),
    axisLine: { lineStyle: { color: '#dccfc2' } }, axisTick: { show: false },
    axisLabel: { color: '#6e5b50', fontSize: 12, hideOverlap: true, formatter: (date: string) => date.slice(5).replace('-', '/') },
  },
  yAxis: {
    type: 'value', min: 0, minInterval: 1, max: trendTotal.value === 0 ? 1 : undefined,
    axisLabel: { color: '#6e5b50', fontSize: 12 }, splitLine: { lineStyle: { color: '#e9dfd5' } },
  },
  series: [{ name: trendTitle.value, type: 'bar', data: trend.value.map(day => day[metric.value]), barMaxWidth: 32, itemStyle: { borderRadius: [3, 3, 0, 0] } }],
}))
watch(chartOption, value => chart?.setOption(value, { notMerge: true }))
onMounted(load)
</script>

<template>
  <div class="admin-page operations-overview" aria-label="运营总览" :aria-busy="busy">
    <header class="page-heading overview-heading">
      <div><h1>运营总览</h1><p>用户增长、创作表现与积分流向 <span>· 今日按 {{ stats?.trend_timezone || 'UTC' }} 统计</span></p></div>
      <div class="overview-refresh">
        <span v-if="updatedAt">更新于 {{ updatedAt }}</span>
        <UiButton type="button" class="button" :disabled="busy" @click="load">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M16.2 7a6.5 6.5 0 1 0 .1 5M16.2 3v4.5h-4.5" /></svg>
          {{ busy ? '读取中…' : '刷新统计' }}
        </UiButton>
      </div>
    </header>

    <div v-if="error" class="overview-error" role="alert">
      <div><strong>{{ stats ? '统计刷新未完成' : '暂时无法读取运营数据' }}</strong><p>{{ error }}{{ stats ? '。当前保留上次读取的统计。' : '，请稍后重新加载。' }}</p></div>
      <UiButton type="button" class="button" :disabled="busy" @click="load">重新加载</UiButton>
    </div>
    <div v-if="busy" class="overview-loading" role="status">
      <p>正在读取统计…</p>
      <div v-if="!stats" class="loading-shape" aria-hidden="true"><span /><span /><span /><span /></div>
    </div>

    <template v-if="stats">
      <section class="overview-metrics" aria-label="平台累计指标">
        <div data-metric="total-users"><span class="metric-label">注册用户</span><strong>{{ number(stats.total_users) }}<small>人</small></strong><span class="metric-note">普通用户累计</span></div>
        <div data-metric="registered-today"><span class="metric-label">今日注册</span><strong>{{ number(stats.registered_today) }}<small>人</small></strong><span class="metric-note">近 {{ stats.trend_days || 14 }} 天新增 {{ number(stats.registered_in_trend) }}</span></div>
        <div data-metric="active-today"><span class="metric-label">今日活跃</span><strong>{{ number(stats.active_today) }}<small>人</small></strong><span class="metric-note">提交创作的去重用户</span></div>
        <div><span class="metric-label">累计任务</span><strong>{{ number(stats.generated_count) }}<small>次</small></strong><span class="metric-note">今日 {{ number(today?.task_count) }} 次</span></div>
        <div><span class="metric-label">整体成功率</span><strong :class="{ 'metric-no-sample': stats.success_rate == null }">{{ rate(stats.success_rate) }}</strong><span class="metric-note">{{ number(stats.terminal_count) }} 个终态任务</span></div>
        <div><span class="metric-label">累计消费积分</span><strong>{{ number(stats.credits_consumed) }}<small>积分</small></strong><span class="metric-note">仅统计已完成消费</span></div>
      </section>

      <div v-if="stats.generated_count === 0" class="overview-empty">
        <strong>暂无任务记录</strong><p>任务受理后，这里会展示真实用量。已配置的 Agent 仍可在下方查看。</p>
      </div>

      <div class="overview-charts">
        <section class="overview-panel user-panel" aria-label="用户增长与活跃">
          <div class="chart-heading"><h2>用户增长与活跃</h2><span class="trend-period">近 {{ stats.trend_days || 14 }} 天</span></div>
          <div class="period-summary"><span>近 {{ stats.trend_days || 14 }} 天注册 <strong>{{ number(stats.registered_in_trend) }}</strong> 人</span><span>期间活跃 <strong>{{ number(stats.active_in_trend) }}</strong> 人</span></div>
          <UserActivityChart v-if="userTrendAvailable" :days="trend" />
          <p v-else class="chart-empty">暂未提供用户趋势数据。</p>
          <p class="panel-note">活跃：提交过创作任务的去重用户；不含管理员。</p>
        </section>
        <section class="overview-panel trend-panel" aria-label="日趋势">
          <div class="chart-heading">
            <h2>创作趋势</h2>
            <div class="chart-switch" role="group" aria-label="趋势指标">
              <UiButton type="button" class="button" :class="{ primary: metric === 'task_count' }" :aria-pressed="metric === 'task_count'" @click="metric = 'task_count'">任务量</UiButton>
              <UiButton type="button" class="button" :class="{ primary: metric === 'credits_consumed' }" :aria-pressed="metric === 'credits_consumed'" @click="metric = 'credits_consumed'">消费积分</UiButton>
            </div>
          </div>
          <div class="period-summary"><span>近 {{ stats.trend_days || 14 }} 天{{ trendTitle }} <strong>{{ number(trendTotal) }}</strong> {{ metric === 'task_count' ? '次' : '积分' }}</span></div>
          <template v-if="stats.daily_trend !== undefined">
            <div ref="chartElement" class="trend-chart" role="img" :aria-label="trendDescription" />
            <p v-if="!trend.length" class="chart-empty">这段时间暂无日趋势记录。</p>
            <p v-else-if="trendTotal === 0" class="chart-empty">这段时间暂无{{ metric === 'task_count' ? '任务' : '积分消费' }}，图中各日均为 0。</p>
          </template>
          <p v-else class="chart-empty">暂未提供日趋势数据。</p>
        </section>

        <section class="overview-panel state-panel" aria-label="任务状态分布">
          <div class="chart-heading"><h2>任务状态</h2><span class="trend-period">累计</span></div>
          <div class="state-summary"><span>未结算任务 <strong>{{ number(stats.unsettled_count) }}</strong></span><span>当前冻结 <strong>{{ number(stats.credits_frozen) }}</strong> 积分</span></div>
          <p v-if="stats.state_counts === undefined" class="chart-empty">暂未提供状态分布。</p>
          <p v-else-if="!stateRows.length" class="chart-empty">暂无任务状态记录。</p>
          <dl v-else class="state-distribution">
            <div v-for="row in stateRows" :key="row.state">
              <dt>{{ row.name }}</dt><dd>{{ number(row.count) }}<small>次</small></dd>
              <div class="state-track" aria-hidden="true"><span :class="{ 'state-track-success': row.state === 'SUCCEEDED' }" :style="{ width: share(row.count, stats.generated_count) + '%' }" /></div>
            </div>
          </dl>
        </section>
      </div>

      <section class="overview-panel agent-panel" aria-label="Agent 运行对比">
        <div class="chart-heading"><h2>Agent 运行对比</h2><span class="trend-period">全部历史任务</span></div>
        <p v-if="namesUnavailable" class="names-unavailable">Agent 名称未能加载，已显示有统计记录的 Agent 标识。刷新可重试。</p>
        <div class="agent-legend" aria-label="任务结果图例"><span v-for="segment in segments" :key="segment.key"><i :style="{ background: segment.color }" />{{ segment.name }}</span><span><i class="legend-active" />进行中</span></div>
        <p v-if="!agentRows.length" class="chart-empty">暂无 Agent 记录，配置 Agent 并受理任务后可查看运行对比。</p>
        <article v-for="agent in agentRows" :key="agent.id" :data-agent-id="agent.id" class="agent-row">
          <div class="agent-identity"><strong>{{ agent.name }}</strong><span v-if="agent.kind">{{ agent.kind }} Agent</span><small v-else>{{ agent.id }}</small></div>
          <template v-if="agent.usage">
            <div class="agent-task">
              <div class="agent-task-heading"><span>任务量</span><strong>{{ number(agent.usage.task_count) }}<small>次</small></strong></div>
              <div class="agent-task-bar" aria-hidden="true">
                <span v-for="segment in segments" :key="segment.key" :style="{ width: share(agent.usage[segment.key], agent.usage.task_count) + '%', background: segment.color }" />
                <span class="legend-active" :style="{ width: share(activeCount(agent.usage), agent.usage.task_count) + '%' }" />
              </div>
              <p v-if="agent.usage.task_count === 0" class="agent-result">暂无任务</p>
              <p v-else class="agent-result">成功 {{ number(agent.usage.succeeded_count) }} · 失败 {{ number(agent.usage.failed_count) }} · 人工关闭 {{ number(agent.usage.manually_closed_count) }} · 进行中 {{ number(activeCount(agent.usage)) }}</p>
            </div>
            <dl class="agent-values">
              <div><dt>成功率</dt><dd :class="{ 'value-no-sample': agent.usage.success_rate == null }">{{ rate(agent.usage.success_rate) }}</dd></div>
              <div><dt>消费积分</dt><dd>{{ number(agent.usage.credits_consumed) }}</dd></div>
              <div><dt>冻结积分</dt><dd>{{ number(agent.usage.credits_frozen) }}</dd></div>
              <div><dt>累计释放</dt><dd>{{ number(agent.usage.credits_released) }}</dd></div>
            </dl>
          </template>
          <p v-else class="chart-empty">暂未提供此 Agent 的统计。</p>
        </article>
      </section>

      <section class="overview-accounting" aria-label="积分入账与释放">
        <h2>积分流向</h2>
        <dl><div><dt>注册赠送</dt><dd>{{ number(stats.signup_credits) }}<small>积分</small></dd></div><div><dt>管理员发放</dt><dd>{{ number(stats.admin_granted_credits) }}<small>积分</small></dd></div><div><dt>当前冻结</dt><dd>{{ number(stats.credits_frozen) }}<small>积分</small></dd></div><div><dt>累计释放</dt><dd>{{ number(stats.credits_released) }}<small>积分</small></dd></div></dl>
      </section>
    </template>
  </div>
</template>

<style scoped>
.operations-overview { display:grid; gap:14px; padding-bottom:16px; font-size:14px; line-height:1.5; font-variant-numeric:tabular-nums; }
.overview-heading { display:flex; align-items:center; justify-content:space-between; gap:16px; }
.operations-overview .overview-heading h1 { margin:0; font-size:24px; }
.operations-overview .overview-heading p { margin:4px 0 0; font-size:13px; }
.overview-heading p span { white-space:nowrap; }
.operations-overview h2 { margin:0; font-size:15px; font-weight:600; }
.overview-refresh { display:flex; align-items:center; gap:12px; }
.overview-refresh > span,.trend-period { font-size:12px; color:var(--color-muted); }
.overview-refresh svg { width:16px; height:16px; fill:none; stroke:currentColor; stroke-width:1.5; stroke-linecap:round; stroke-linejoin:round; margin-right:6px; }
.overview-error { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:14px 16px; border:1px solid #dfb9a9; border-radius:12px; background:#fbebe3; color:var(--color-danger); }
.overview-error p { margin:4px 0 0; font-size:14px; color:inherit; }
.overview-loading p { margin:0; font-size:14px; }
.loading-shape { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; padding:16px 0; }
.loading-shape span { height:48px; border-radius:8px; background:var(--color-sidebar); }
.overview-metrics { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:0; padding:12px 0; border:1px solid var(--color-border); border-radius:12px; background:var(--color-panel); }
.overview-metrics > div { display:flex; align-items:baseline; flex-wrap:wrap; gap:4px 10px; min-width:0; padding:0 18px; border-inline-start:1px solid var(--color-border); }
.overview-metrics > div:first-child { border-inline-start:0; }
.metric-label { font-size:13px; color:var(--color-muted); }
.overview-metrics strong { width:100%; font-size:26px; font-weight:600; line-height:1.4; overflow-wrap:anywhere; }
.overview-metrics .metric-no-sample { font-size:14px; }
.overview-metrics small { margin-left:4px; font-size:12px; font-weight:400; }
.metric-note { flex-basis:100%; color:var(--color-muted); font-size:12px; }
.overview-empty { padding:12px 16px; background:var(--color-selected); border-radius:12px; }
.overview-empty p { margin:4px 0 0; font-size:13px; }
.overview-charts { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.1fr) minmax(200px,.65fr); gap:14px; align-items:stretch; }
.overview-panel { min-width:0; padding:14px 16px; border:1px solid var(--color-border); border-radius:12px; background:var(--color-panel); }
.chart-heading { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-bottom:12px; min-height:32px; }
.period-summary { display:flex; align-items:baseline; flex-wrap:wrap; gap:6px 18px; min-height:30px; margin-bottom:8px; font-size:12px; color:var(--color-muted); }
.period-summary strong { margin-inline:4px; font-size:18px; font-weight:600; color:var(--color-text); }
.panel-note { margin:8px 0 0; font-size:12px; color:var(--color-muted); }
.state-summary { display:grid; gap:4px; padding-bottom:12px; margin-bottom:12px; border-bottom:1px solid var(--color-border); font-size:12px; color:var(--color-muted); }
.state-summary strong { color:var(--color-text); }
.chart-switch { display:flex; gap:4px; }
.chart-switch .button { padding:6px 8px; margin:0; min-height:32px; font-size:12px; }
.trend-chart { display:block; width:100%; height:208px; overflow:hidden; }
.trend-chart :deep(svg) { width:100%; height:100%; }
.chart-empty { margin:12px 0; font-size:13px; color:var(--color-muted); }
.state-distribution { margin:0; max-height:220px; overflow:auto; }
.state-distribution > div { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:4px 12px; padding-bottom:10px; }
.state-distribution dt { font-size:13px; color:var(--color-muted); }
.state-distribution dd { margin:0; font-size:14px; font-weight:600; }
.state-distribution small { margin-left:4px; font-weight:400; }
.state-track { grid-column:1/-1; height:4px; border-radius:3px; background:#eee5dc; overflow:hidden; }
.state-track span { display:block; height:100%; background:#ae8c70; }
.state-track .state-track-success { background:var(--color-primary); }
.agent-legend { display:flex; flex-wrap:wrap; gap:16px; font-size:12px; color:var(--color-muted); margin-bottom:8px; }
.agent-legend > span { display:flex; align-items:center; gap:6px; }
.agent-legend i { width:8px; height:8px; border-radius:2px; }
.legend-active { background:#d9cbbb; }
.agent-row { display:grid; grid-template-columns:minmax(110px,.65fr) minmax(180px,1.4fr) minmax(340px,2fr); gap:20px; align-items:center; padding:10px 0; border-top:1px solid var(--color-border); }
.agent-identity { min-width:0; }
.agent-identity > strong { display:block; margin:0 0 4px; font-size:14px; font-weight:600; overflow-wrap:anywhere; }
.agent-identity > span,.agent-identity > small { display:block; font-size:12px; color:var(--color-muted); overflow-wrap:anywhere; }
.agent-task-heading { display:flex; align-items:baseline; justify-content:space-between; gap:8px; font-size:12px; color:var(--color-muted); }
.agent-task-heading strong { font-size:15px; font-weight:600; color:var(--color-text); }
.agent-task-heading small { font-weight:400; margin-left:4px; }
.agent-task-bar { display:flex; height:5px; border-radius:4px; overflow:hidden; background:#eee5dc; margin-top:6px; }
.agent-task-bar span { height:100%; flex-shrink:0; }
.agent-result { font-size:12px; margin:6px 0 0; color:var(--color-muted); }
.agent-values { display:grid; grid-template-columns:1.4fr repeat(3,1fr); gap:12px; margin:0; }
.agent-values > div { min-width:0; text-align:right; }
.agent-values dt { font-size:12px; color:var(--color-muted); margin-bottom:4px; white-space:nowrap; }
.agent-values dd { font-size:15px; font-weight:600; margin:0; overflow-wrap:anywhere; }
.agent-values .value-no-sample { font-size:12px; font-weight:400; line-height:21px; }
.names-unavailable { font-size:13px; margin:0 0 12px; }
.overview-accounting { display:flex; align-items:center; gap:24px; padding:14px 16px; border:1px solid var(--color-border); border-radius:12px; background:var(--color-panel); }
.overview-accounting h2 { flex-shrink:0; }
.overview-accounting dl { display:flex; flex:1; justify-content:space-between; flex-wrap:wrap; gap:12px 24px; margin:0; }
.overview-accounting dl > div { display:flex; align-items:baseline; gap:12px; }
.overview-accounting dt { color:var(--color-muted); font-size:12px; }
.overview-accounting dd { font-size:15px; margin:0; font-weight:600; }
.overview-accounting small { font-size:12px; font-weight:400; margin-left:5px; }
@media (max-width:1350px) {
  .overview-metrics { grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px 0; }
  .overview-metrics > div:nth-child(4) { border-inline-start:0; }
  .overview-charts { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .state-panel { grid-column:1/-1; }
  .state-summary { display:flex; gap:24px; }
  .state-distribution { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:0 24px; max-height:none; }
}
@media (max-width:1100px) {
  .agent-row { grid-template-columns:minmax(110px,.7fr) minmax(200px,1.3fr); gap:12px 24px; }
  .agent-values { grid-column:1/-1; }
  .agent-values > div { text-align:left; }
  .overview-accounting { align-items:flex-start; flex-direction:column; gap:12px; }
  .overview-accounting dl { width:100%; }
}
@media (max-width:850px) {
  .overview-charts { grid-template-columns:minmax(0,1fr); gap:12px; }
  .state-distribution { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); column-gap:24px; }
}
@media (max-width:600px) {
  .operations-overview { gap:12px; }
  .overview-heading { align-items:flex-start; flex-wrap:wrap; }
  .overview-refresh { width:100%; justify-content:space-between; }
  .overview-metrics { grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px 0; }
  .overview-metrics > div { gap:3px 6px; padding:0 12px; }
  .overview-metrics > div:nth-child(4) { border-inline-start:1px solid var(--color-border); }
  .overview-metrics > div:nth-child(odd) { border-inline-start:0; }
  .overview-metrics strong { font-size:24px; }
  .overview-metrics .metric-no-sample { font-size:13px; }
  .chart-heading { gap:8px; }
  .chart-switch .button { min-height:44px; }
  .trend-chart { height:216px; }
  .agent-row { grid-template-columns:minmax(0,1fr); gap:10px; }
  .agent-identity { display:flex; align-items:baseline; justify-content:space-between; gap:12px; }
  .agent-identity > strong { margin:0; }
  .agent-values { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .overview-error { align-items:flex-start; flex-direction:column; }
  .overview-refresh > span { font-size:12px; }
}
@media (pointer:coarse) { .chart-switch .button { min-height:44px; } }
</style>
