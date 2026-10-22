import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import UserActivityChart from '../../src/features/admin/UserActivityChart.vue'

const charts = vi.hoisted(() => ({ init: vi.fn(), use: vi.fn(), setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }))
vi.mock('echarts/core', () => ({ init: charts.init, use: charts.use }))
beforeEach(() => {
  vi.resetAllMocks()
  charts.init.mockReturnValue(charts)
})
afterEach(() => vi.unstubAllGlobals())

it('plots registration and activity as distinct series, preserving missing values and zero', async () => {
  const wrapper = mount(UserActivityChart, { props: { days: [
    { date: '2026-10-20', registered_count: 0, active_user_count: 2 },
    { date: '2026-10-21', registered_count: 3 },
  ] } })
  await flushPromises()
  const option = charts.setOption.mock.calls.at(-1)![0]
  expect(option.series[0].data).toEqual([0, 3])
  expect(option.series[1].data).toEqual([2, null])
  expect(option.series[0].lineStyle.type).not.toBe(option.series[1].lineStyle.type)
  expect(wrapper.get('[role="img"]').attributes('aria-label')).toContain('2026-10-21：注册 3 人，活跃 未提供 人')
  await wrapper.setProps({ days: [{ date: '2026-10-21', registered_count: 0, active_user_count: 0 }] })
  expect(charts.setOption.mock.calls.at(-1)![0].yAxis.max).toBe(1)
  expect(charts.setOption.mock.calls.at(-1)![0].series[1].data).toEqual([0])
  window.dispatchEvent(new Event('resize'))
  expect(charts.resize).toHaveBeenCalledOnce()
  wrapper.unmount()
  expect(charts.dispose).toHaveBeenCalledOnce()
  window.dispatchEvent(new Event('resize'))
  expect(charts.resize).toHaveBeenCalledOnce()
})
