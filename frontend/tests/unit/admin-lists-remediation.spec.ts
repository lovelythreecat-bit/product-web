import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
const api = vi.hoisted(() => ({
  listTasks: vi.fn(), listAgents: vi.fn(), listUsers: vi.fn(), tasksSummary: vi.fn(), listInvestigations: vi.fn(),
  listAdminLedger: vi.fn(), ledgerSummary: vi.fn(), usersSummary: vi.fn(), listAudit: vi.fn(), auditSummary: vi.fn(),
}))
vi.mock('../../src/api/admin', () => api)
vi.mock('vue-router', () => ({ useRoute: () => ({ query: {} }) }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: { value: 0 }, profile: { value: { user_id: 'admin' } } }, onIdentityChange: () => () => {} }))
vi.mock('../../src/features/admin/creditIntent', () => ({ restoreGrant: () => null, rememberGrant: vi.fn(), forgetGrant: vi.fn() }))
import TasksView from '../../src/features/admin/TasksView.vue'
import CreditsView from '../../src/features/admin/CreditsView.vue'
import AuditView from '../../src/features/admin/AuditView.vue'
const cases = [
  { name: 'tasks', component: TasksView, request: api.listTasks, input: '#admin-task-keyword', row: (id: string) => ({ id, user_id: 'u1', account: id, state: 'RUNNING', settlement_state: 'FROZEN', agent_id: 'a1', agent_version: 'v1', elapsed_seconds: 1, fixed_credits: 3 }) },
  { name: 'credits', component: CreditsView, request: api.listAdminLedger, input: '#admin-ledger-keyword', row: (id: string) => ({ ledger_id: 'hidden-ledger-id', user_id: 'u1', account: id, amount: 3, kind: 'consume', task_id: 'hidden-task-id', task_name: '陶瓷杯商品图', reason: '仅详情保留的原因', created_at: '2026-10-17T00:00:00Z', balances_before: { available: 1 }, balances_after: { available: 4 } }) },
  { name: 'audit', component: AuditView, request: api.listAudit, input: '#admin-audit-keyword', row: (id: string) => ({ id, action: 'admin_credit_grant', actor_id: null, object_id: 'hidden-object-id', reason: id, created_at: '2026-10-17T00:00:00Z', changes: {} }) },
]
function button(wrapper: VueWrapper, name: string) { return wrapper.findAll('button').find(item => (name === '上一页' ? item.classes().includes('btn-prev') : name === '下一页' ? item.classes().includes('btn-next') : item.text() === name))! }
beforeEach(() => {
  vi.resetAllMocks()
  api.listUsers.mockResolvedValue({ items: [], next_cursor: null, total: 21, page_size: 20 })
  api.listAgents.mockResolvedValue([])
  api.tasksSummary.mockResolvedValue({ total: 900 })
  api.usersSummary.mockResolvedValue({ total: 900 })
  api.ledgerSummary.mockResolvedValue({ ledger_count: 900 })
  api.auditSummary.mockResolvedValue({ total: 900, action_counts: {} })
  for (const item of cases) item.request.mockResolvedValue({ items: [item.row('first-row')], next_cursor: 'cursor-two', total: 21, page_size: 20 })
})
it.each(cases)('$name keeps just the query and list without aggregate or unrelated modules', async item => {
  const wrapper = mount(item.component, { global: { stubs: { ContentAccessPanel: true, RouterLink: true } } })
  await flushPromises()
  expect(wrapper.findAll('.panel')).toHaveLength(1)
  expect(wrapper.findAll('form')).toHaveLength(1)
  expect(wrapper.text()).not.toMatch(/平台任务汇总|平台审计汇总|待核查记录|接收用户|汇总覆盖|先查原任务|查询操作人/)
  expect(wrapper.findAll('button').some(button => /^(发放积分|配置注册赠送)$/.test(button.text()))).toBe(false)
  expect(api.tasksSummary).not.toHaveBeenCalled()
  expect(api.auditSummary).not.toHaveBeenCalled()
  expect(api.ledgerSummary).not.toHaveBeenCalled()
  expect(api.usersSummary).not.toHaveBeenCalled()
  expect(wrapper.findAll('button').some(item => item.text().includes('加载更多'))).toBe(false)
  if (item.name === 'credits') {
    expect(wrapper.text()).toContain('陶瓷杯商品图')
    expect(wrapper.text()).not.toMatch(/hidden-ledger-id|hidden-task-id|仅详情保留的原因/)
  }
  if (item.name === 'audit') expect(wrapper.text()).not.toContain('hidden-object-id')
  wrapper.unmount()
})
it.each(cases)('$name replaces rows when paging and keeps applied filters until a new query succeeds', async item => {
  const wrapper = mount(item.component, { global: { stubs: { ContentAccessPanel: true, RouterLink: true } } })
  await flushPromises()
  expect(button(wrapper, '上一页').attributes('disabled')).toBeDefined()
  await wrapper.get(item.input).setValue('已查询')
  await wrapper.get('form').trigger('submit'); await flushPromises()
  await wrapper.get(item.input).setValue('未查询草稿')
  item.request.mockResolvedValueOnce({ items: [item.row('second-row')], next_cursor: null, total: 21, page_size: 20 })
  await button(wrapper, '下一页').trigger('click'); await flushPromises()
  expect(wrapper.text()).toContain('second-row')
  expect(wrapper.text()).not.toContain('first-row')
  expect(wrapper.findComponent({ name: 'ElPagination' }).props('currentPage')).toBe(2)
  expect(item.request.mock.calls.at(-1)?.at(-1)).toBe(2)
  expect(item.request.mock.calls.at(-1)).toContain('已查询')
  expect(item.request.mock.calls.at(-1)).not.toContain('未查询草稿')
  expect(button(wrapper, '下一页').attributes('disabled')).toBeDefined()
  await button(wrapper, '上一页').trigger('click'); await flushPromises()
  expect(wrapper.text()).toContain('first-row')
  expect(wrapper.text()).not.toContain('second-row')
  expect(wrapper.findComponent({ name: 'ElPagination' }).props('currentPage')).toBe(1)
  expect(item.request.mock.calls.at(-1)?.[0]).toBeUndefined()
  expect(item.request.mock.calls.at(-1)).toContain('已查询')
  expect(item.request.mock.calls.at(-1)).not.toContain('未查询草稿')
  await wrapper.get('form').trigger('submit'); await flushPromises()
  expect(item.request.mock.calls.at(-1)).toContain('未查询草稿')
  expect(wrapper.findComponent({ name: 'ElPagination' }).props('currentPage')).toBe(1)
  wrapper.unmount()
})
it.each(cases)('$name preserves rows and page after a failed next-page request and disables pagination while loading', async item => {
  const wrapper = mount(item.component, { global: { stubs: { ContentAccessPanel: true, RouterLink: true } } })
  await flushPromises()
  let reject!: (reason: Error) => void
  item.request.mockReturnValueOnce(new Promise((_resolve, fail) => { reject = fail }))
  await button(wrapper, '下一页').trigger('click')
  expect(button(wrapper, '上一页').attributes('disabled')).toBeDefined()
  expect(button(wrapper, '下一页').attributes('disabled')).toBeDefined()
  reject(new Error('分页请求失败')); await flushPromises()
  expect(wrapper.text()).toContain('分页请求失败')
  expect(wrapper.text()).toContain('first-row')
  expect(wrapper.findComponent({ name: 'ElPagination' }).props('currentPage')).toBe(1)
  expect(button(wrapper, '下一页').attributes('disabled')).toBeUndefined()
  item.request.mockResolvedValueOnce({ items: [item.row('second-row')], next_cursor: null, total: 21, page_size: 20 })
  await button(wrapper, '下一页').trigger('click'); await flushPromises()
  expect(item.request.mock.calls.at(-1)?.at(-1)).toBe(2)
  expect(wrapper.findComponent({ name: 'ElPagination' }).props('currentPage')).toBe(2)
  wrapper.unmount()
})

it.each(cases)('$name jumps directly to an unvisited page with the applied filter', async item => {
  item.request.mockResolvedValueOnce({ items: [item.row('first')], total: 123, page: 1, page_size: 20, next_cursor: null })
  const wrapper = mount(item.component, { global: { stubs: { RouterLink: true } } })
  await flushPromises()
  item.request.mockResolvedValueOnce({ items: [item.row('fifth')], total: 123, page: 5, page_size: 20, next_cursor: null })
  wrapper.findComponent({ name: 'ElPagination' }).vm.$emit('current-change', 5)
  await flushPromises()
  expect(item.request.mock.calls.at(-1)?.at(-1)).toBe(5)
  expect(item.request.mock.calls.at(-1)?.[0]).toBeUndefined()
  expect(wrapper.findComponent({ name: 'ElPagination' }).props('currentPage')).toBe(5)
  expect(wrapper.text()).toContain('fifth')
  wrapper.unmount()
})
