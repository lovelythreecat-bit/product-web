import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'

const api = vi.hoisted(() => ({ listLedger: vi.fn(), refreshAccount: vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }))
vi.mock('../../src/api/account', () => ({ listLedger: api.listLedger }))
vi.mock('../../src/features/auth/session', () => ({ session: {
  profile: { value: { account: 'merchant', nickname: '小陶商店', status: 'active' } },
  account: { value: { available: 90, frozen: 10, consumed: 20, credited_total: 120 } },
  epoch: { value: 1 }, busy: { value: false }, refreshAccount: api.refreshAccount,
} }))
import AccountView from '../../src/features/account/AccountView.vue'

const overlay = defineComponent({ template: '<div />' })
const global = { stubs: { AppDrawer: overlay, ChangePasswordDrawer: true, UserAvatar: true, RouterLink: { template: '<a><slot /></a>' } } }
const entry = (id: string) => ({ ledger_id: id, kind: 'admin_grant', amount: 8, created_at: '2026-10-18T00:00:00Z', task_id: null, reason: '积分发放', balances_before: { available: 0, frozen: 0, consumed: 0 }, balances_after: { available: 8, frozen: 0, consumed: 0 } })
const button = (wrapper: ReturnType<typeof mount>, label: string) => wrapper.findAll('button').find(item => (label === '上一页' ? item.classes().includes('btn-prev') : label === '下一页' ? item.classes().includes('btn-next') : item.text() === label))!
beforeEach(() => { vi.clearAllMocks(); api.refreshAccount.mockResolvedValue(undefined) })

it('shows one numbered page at a time and reloads a previous page', async () => {
  api.listLedger.mockResolvedValueOnce({ items: [entry('first')], next_cursor: 'cursor-2', total: 21, page_size: 20 }).mockResolvedValueOnce({ items: [entry('second')], next_cursor: null, total: 21, page_size: 20 })
  const wrapper = mount(AccountView, { global }); await flushPromises()
  expect(wrapper.find('[data-ledger-id="first"]').exists()).toBe(true)
  expect(button(wrapper, '上一页').attributes('disabled')).toBeDefined()
  await button(wrapper, '下一页').trigger('click'); await flushPromises()
  expect(api.listLedger).toHaveBeenLastCalledWith(undefined, {}, 2)
  expect(wrapper.find('[data-ledger-id="first"]').exists()).toBe(false)
  expect(wrapper.find('[data-ledger-id="second"]').exists()).toBe(true)
  expect(wrapper.findComponent({ name: 'ElPagination' }).props('currentPage')).toBe(2)
  expect(button(wrapper, '下一页').attributes('disabled')).toBeDefined()
  api.listLedger.mockResolvedValueOnce({ items: [entry('first')], next_cursor: 'cursor-2', total: 21, page_size: 20 });
  await button(wrapper, '上一页').trigger('click'); await flushPromises()
  expect(wrapper.find('[data-ledger-id="first"]').exists()).toBe(true)
  expect(wrapper.find('[data-ledger-id="second"]').exists()).toBe(false)
  expect(api.listLedger).toHaveBeenCalledTimes(3)
  wrapper.unmount()
})

it('retains the current page when fetching the next page fails and permits retry', async () => {
  api.listLedger.mockResolvedValueOnce({ items: [entry('first')], next_cursor: 'cursor-2', total: 21, page_size: 20 }).mockRejectedValueOnce(Error('offline')).mockResolvedValueOnce({ items: [entry('second')], next_cursor: null, total: 21, page_size: 20 })
  const wrapper = mount(AccountView, { global }); await flushPromises()
  await button(wrapper, '下一页').trigger('click'); await flushPromises()
  expect(wrapper.find('[data-ledger-id="first"]').exists()).toBe(true)
  expect(wrapper.text()).toContain('积分记录暂时无法读取，请重试。')
  expect(wrapper.findComponent({ name: 'ElPagination' }).props('currentPage')).toBe(1)
  await button(wrapper, '下一页').trigger('click'); await flushPromises()
  expect(wrapper.find('[data-ledger-id="second"]').exists()).toBe(true)
  wrapper.unmount()
})

it('refreshes from the first page and discards cached pages from the old ledger snapshot', async () => {
  api.listLedger.mockResolvedValueOnce({ items: [entry('first')], next_cursor: 'cursor-2', total: 21, page_size: 20 }).mockResolvedValueOnce({ items: [entry('second')], next_cursor: null, total: 21, page_size: 20 }).mockResolvedValueOnce({ items: [entry('new-first')], next_cursor: null, total: 1, page_size: 20 })
  const wrapper = mount(AccountView, { global }); await flushPromises()
  await button(wrapper, '下一页').trigger('click'); await flushPromises()
  await button(wrapper, '刷新记录').trigger('click'); await flushPromises()
  expect(api.listLedger).toHaveBeenLastCalledWith(undefined, {}, 1)
  expect(wrapper.find('[data-ledger-id="new-first"]').exists()).toBe(true)
  expect(wrapper.find('[data-ledger-id="second"]').exists()).toBe(false)
  expect(wrapper.findComponent({ name: 'ElPagination' }).props('currentPage')).toBe(1)
  expect(button(wrapper, '上一页').attributes('disabled')).toBeDefined()
  expect(button(wrapper, '下一页').attributes('disabled')).toBeDefined()
  wrapper.unmount()
})

it('queries inclusive selected dates, clears cached pages, and renders server-wide consumption', async () => {
  api.listLedger.mockResolvedValueOnce({ items: [entry('old')], next_cursor: 'old-cursor', total: 21, page_size: 20, consumption: { copy: 9, image: 12, video: 30, other: 0 } }).mockResolvedValueOnce({ items: [{ ...entry('filtered'), task_id: 'task-uuid', task_name: '陶瓷杯图片' }], next_cursor: null, total: 21, page_size: 20, consumption: { copy: 5, image: 8, video: 20, other: 0 } })
  const wrapper = mount(AccountView, { global }); await flushPromises()
  expect(wrapper.find('.consumption-summary').text()).toContain('文案 9')
  expect(wrapper.find('.consumption-summary').text()).toContain('视频 30')
  await wrapper.get('#ledger-start-date').setValue('2026-10-20')
  await wrapper.get('#ledger-end-date').setValue('2026-10-20')
  await wrapper.get('.ledger-filters').trigger('submit'); await flushPromises()
  expect(api.listLedger).toHaveBeenLastCalledWith(undefined, { start_time: new Date('2026-10-20T00:00:00').toISOString(), end_time: new Date('2026-10-21T00:00:00').toISOString() }, 1)
  expect(wrapper.text()).toContain('陶瓷杯图片')
  expect(wrapper.find('.ledger-table').text()).not.toContain('task-uuid')
  expect(wrapper.find('[data-ledger-id="old"]').exists()).toBe(false)
  expect(wrapper.find('.consumption-summary').text()).toContain('文案 5')
  expect(wrapper.find('[data-testid="consumed"]').text()).toBe('20')
  expect(wrapper.find('.account-explanation').exists()).toBe(false)
  expect(wrapper.findComponent({ name: 'ElTable' }).props('height')).toBe('100%')
  wrapper.unmount()
})

it('rejects a reversed date range without requesting or losing the current records', async () => {
  api.listLedger.mockResolvedValue({ items: [entry('old')], next_cursor: null, total: 21, page_size: 20 })
  const wrapper = mount(AccountView, { global }); await flushPromises()
  await wrapper.get('#ledger-start-date').setValue('2026-10-21')
  await wrapper.get('#ledger-end-date').setValue('2026-10-20')
  await wrapper.get('.ledger-filters').trigger('submit'); await flushPromises()
  expect(api.listLedger).toHaveBeenCalledTimes(1)
  expect(wrapper.text()).toContain('开始日期不能晚于结束日期')
  expect(wrapper.find('[data-ledger-id="old"]').exists()).toBe(true)
  wrapper.unmount()
})

it('retains applied dates and totals when a replacement filter request fails', async () => {
  api.listLedger.mockResolvedValueOnce({ items: [entry('old')], next_cursor: 'cursor-2', total: 21, page_size: 20, consumption: { copy: 5, image: 8, video: 20, other: 0 } }).mockRejectedValueOnce(Error('offline')).mockResolvedValueOnce({ items: [entry('next')], next_cursor: null, total: 21, page_size: 20 })
  const wrapper = mount(AccountView, { global }); await flushPromises()
  await wrapper.get('#ledger-start-date').setValue('2026-10-20')
  await wrapper.get('.ledger-filters').trigger('submit'); await flushPromises()
  expect(wrapper.find('[data-ledger-id="old"]').exists()).toBe(true)
  expect(wrapper.find('.consumption-summary').text()).toContain('文案 5')
  await button(wrapper, '下一页').trigger('click'); await flushPromises()
  expect(api.listLedger).toHaveBeenLastCalledWith(undefined, {}, 2)
  wrapper.unmount()
})
