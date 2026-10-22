import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import UsageView from '../../src/features/admin/UsageView.vue'

const charts = vi.hoisted(() => ({ init: vi.fn(), use: vi.fn(), setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }))
vi.mock('echarts/core', () => ({ init: charts.init, use: charts.use }))

const api = vi.hoisted(() => ({ statistics: vi.fn(), listAgents: vi.fn() }))
vi.mock('../../src/api/admin', () => api)
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: { value: 0 } } }))

const agent = (agent_id: string, name: string, kind: string) => ({ agent_id, name, kind, version: 'v1' })
const usage = (extra = {}) => ({
  agent_id: 'text', task_count: 5, succeeded_count: 2, failed_count: 1,
  manually_closed_count: 1, terminal_count: 4, success_rate: 0.5,
  unsettled_count: 1, credits_consumed: 8, credits_frozen: 12, credits_released: 20,
  ...extra,
})
const dashboard = (extra = {}) => ({
  generated_count: 5, succeeded_count: 2, terminal_count: 4, success_rate: 0.5,
  success_rate_basis: 'succeeded / (succeeded + failed + manually_closed)',
  credits_consumed: 8, credits_frozen: 12, credits_released: 20,
  signup_credits: 200, admin_granted_credits: 50, unsettled_count: 1,
  supplier_cost_status: 'unavailable', supplier_cost: null,
  supplier_usage_status: 'unavailable', payment_revenue_status: 'not_supported',
  by_agent: [usage()], state_counts: { SUCCEEDED: 2, FAILED: 1, MANUALLY_CLOSED: 1, RUNNING: 1 },
  trend_days: 14, trend_timezone: 'UTC',
  total_users: 40, registered_today: 2, registered_in_trend: 12,
  active_today: 3, active_in_trend: 9, active_user_basis: 'generation_task_created',
  daily_trend: [{ date: '2026-10-16', task_count: 3, credits_consumed: 8 }, { date: '2026-10-17', task_count: 2, credits_consumed: 0 }],
  ...extra,
})

afterEach(() => vi.unstubAllGlobals())

beforeEach(() => {
  vi.resetAllMocks()
  charts.init.mockReturnValue({ setOption: charts.setOption, resize: charts.resize, dispose: charts.dispose })
  api.statistics.mockResolvedValue(dashboard())
  api.listAgents.mockResolvedValue([agent('text', '文案创作', 'text'), agent('image', '图片创作', 'image'), agent('video', '视频创作', 'video')])
})

it('visualizes actual daily values and compares every configured agent, including unused agents', async () => {
  const wrapper = mount(UsageView)
  await flushPromises()
  expect(wrapper.get('h1').text()).toBe('运营总览')
  expect(wrapper.text()).not.toContain('查看每日数据')
  expect(wrapper.findAll('[data-agent-id]')).toHaveLength(3)
  expect(wrapper.get('[data-agent-id="text"]').text()).toContain('50.0%')
  expect(wrapper.get('[data-agent-id="image"]').text()).toContain('暂无终态样本')
  expect(wrapper.get('[data-agent-id="image"]').text()).toContain('暂无任务')
  expect(charts.init).toHaveBeenCalledWith(expect.any(HTMLElement), undefined, { renderer: 'svg' })
  const option = charts.setOption.mock.calls.at(-1)![0]
  expect(option.xAxis.data).toEqual(['2026-10-16', '2026-10-17'])
  expect(option.series[0].data).toEqual([3, 2])
  expect(option.tooltip.trigger).toBe('axis')
  expect(option.tooltip.valueFormatter(0)).toBe('0 次')
  expect(wrapper.text()).toContain('人工关闭')
  expect(wrapper.text()).toContain('UTC')
  await wrapper.findAll('button').find(b => b.text() === '消费积分')!.trigger('click')
  expect(wrapper.get('.trend-chart[role="img"]').attributes('aria-label')).toContain('消费积分')
  const credits = charts.setOption.mock.calls.at(-1)![0]
  expect(credits.series[0].data).toEqual([8, 0])
  expect(credits.tooltip.valueFormatter(8)).toBe('8 积分')
  wrapper.unmount()
})

it('shows registration and distinct creation activity with an explicit period and basis', async () => {
  const wrapper = mount(UsageView)
  await flushPromises()
  expect(wrapper.get('[data-metric="total-users"]').text()).toContain('40')
  expect(wrapper.get('[data-metric="registered-today"]').text()).toContain('2')
  expect(wrapper.get('[data-metric="active-today"]').text()).toContain('3')
  expect(wrapper.get('[aria-label="用户增长与活跃"]').text()).toContain('近 14 天注册')
  expect(wrapper.get('[aria-label="用户增长与活跃"]').text()).toContain('12')
  expect(wrapper.get('[aria-label="用户增长与活跃"]').text()).toContain('9')
  expect(wrapper.text()).toContain('提交过创作任务的去重用户')
  wrapper.unmount()
})

it('does not turn missing user metrics into a zero', async () => {
  api.statistics.mockResolvedValueOnce(dashboard({ total_users: undefined, registered_today: undefined, active_today: undefined }))
  const wrapper = mount(UsageView)
  await flushPromises()
  expect(wrapper.get('[data-metric="total-users"]').text()).toContain('未提供')
  expect(wrapper.get('[data-metric="registered-today"]').text()).toContain('未提供')
  expect(wrapper.get('[data-metric="active-today"]').text()).toContain('未提供')
  wrapper.unmount()
})

it('uses the server success rate, distinguishes zero from missing samples, and does not invent unavailable costs', async () => {
  api.statistics.mockResolvedValue(dashboard({
    success_rate: 0, succeeded_count: 0,
    by_agent: [usage({ succeeded_count: 0, success_rate: 0 })],
  }))
  const wrapper = mount(UsageView)
  await flushPromises()
  expect(wrapper.get('[data-agent-id="text"]').text()).toContain('0.0%')
  expect(wrapper.get('[data-agent-id="video"]').text()).toContain('暂无终态样本')
  expect(wrapper.find('footer[aria-label="统计口径"]').exists()).toBe(false)
  expect(wrapper.text()).not.toContain('¥')
  wrapper.unmount()
})

it('shows an actionable error and retries without fabricating an empty dashboard', async () => {
  api.statistics.mockRejectedValueOnce(new Error('统计服务暂不可用'))
  const wrapper = mount(UsageView)
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('统计服务暂不可用')
  expect(wrapper.find('[data-agent-id]').exists()).toBe(false)
  expect(wrapper.find('.overview-metrics').exists()).toBe(false)
  await wrapper.findAll('button').find(b => b.text() === '重新加载')!.trigger('click')
  await flushPromises()
  expect(wrapper.find('[data-agent-id="text"]').exists()).toBe(true)
  expect(api.statistics).toHaveBeenCalledTimes(2)
  wrapper.unmount()
})

it('retains previous statistics on refresh failure and permits missing agent names', async () => {
  const wrapper = mount(UsageView)
  await flushPromises()
  api.statistics.mockRejectedValueOnce(new Error('刷新失败'))
  await wrapper.findAll('button').find(b => b.text() === '刷新统计')!.trigger('click')
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('保留上次')
  expect(wrapper.find('[data-agent-id="text"]').exists()).toBe(true)
  wrapper.unmount()
  api.listAgents.mockRejectedValueOnce(new Error('名称不可用'))
  const fallback = mount(UsageView)
  await flushPromises()
  expect(fallback.get('[data-agent-id="text"]').text()).toContain('text')
  expect(fallback.text()).toContain('Agent 名称未能加载')
  fallback.unmount()
})

it('keeps real zero trends and empty results distinct from a loading state', async () => {
  let resolve!: (value: unknown) => void
  api.statistics.mockReturnValueOnce(new Promise(r => { resolve = r }))
  const wrapper = mount(UsageView)
  await nextTick()
  expect(wrapper.get('[role="status"]').text()).toContain('正在读取统计')
  resolve(dashboard({
    generated_count: 0, succeeded_count: 0, terminal_count: 0, success_rate: null,
    credits_consumed: 0, credits_frozen: 0, credits_released: 0, unsettled_count: 0,
    by_agent: [], state_counts: {},
    daily_trend: [{ date: '2026-10-16', task_count: 0, credits_consumed: 0 }],
  }))
  await flushPromises()
  expect(wrapper.text()).toContain('暂无任务记录')
  expect(wrapper.text()).toContain('这段时间暂无任务')
  expect(wrapper.find('[role="status"]').exists()).toBe(false)
  expect(charts.setOption.mock.calls.at(-1)![0].series[0].data).toEqual([0])
  expect(charts.setOption.mock.calls.at(-1)![0].yAxis.max).toBe(1)
  expect(wrapper.get('.trend-chart[role="img"]').attributes('aria-label')).toContain('2026-10-16：0次')
  wrapper.unmount()
})


it('resizes with its container and disposes the chart and observer on unmount', async () => {
  let resized!: ResizeObserverCallback
  const disconnect = vi.fn()
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback: ResizeObserverCallback) { resized = callback }
    observe() {}
    disconnect = disconnect
  })
  const wrapper = mount(UsageView)
  await flushPromises()
  resized([], {} as ResizeObserver)
  expect(charts.resize).toHaveBeenCalledOnce()
  window.dispatchEvent(new Event('resize'))
  expect(charts.resize).toHaveBeenCalledTimes(2)
  wrapper.unmount()
  expect(charts.dispose).toHaveBeenCalledOnce()
  expect(disconnect).toHaveBeenCalledOnce()
  window.dispatchEvent(new Event('resize'))
  expect(charts.resize).toHaveBeenCalledTimes(2)
})

it('distinguishes missing and empty trend data without inventing data points', async () => {
  api.statistics.mockResolvedValueOnce(dashboard({ daily_trend: undefined }))
  const missing = mount(UsageView)
  await flushPromises()
  expect(missing.text()).toContain('暂未提供日趋势数据')
  expect(charts.init).not.toHaveBeenCalled()
  missing.unmount()
  api.statistics.mockResolvedValueOnce(dashboard({ daily_trend: [] }))
  const empty = mount(UsageView)
  await flushPromises()
  expect(empty.text()).toContain('这段时间暂无日趋势记录')
  expect(charts.setOption.mock.calls.at(-1)![0].series[0].data).toEqual([])
  empty.unmount()
})
