import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'

const api = vi.hoisted(() => ({ listUsers: vi.fn(), usersSummary: vi.fn(), userAccount: vi.fn(), userLedger: vi.fn(), listAdminLedger: vi.fn(), ledgerSummary: vi.fn(), listAudit: vi.fn(), auditSummary: vi.fn(), listContentGrants: vi.fn(), createContentGrant: vi.fn() }))
const managed = vi.hoisted(() => ({ listUsers: vi.fn(), getUser: vi.fn(), restoreAdjustment: vi.fn(), adjustCredits: vi.fn(), forgetAdjustment: vi.fn() }))
vi.mock('../../src/api/admin', () => api)
vi.mock('../../src/api/adminUsers', () => managed)
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(0), profile: ref({ user_id: 'admin-self-id', account: '当前管理员' }) } }))
import UsersView from '../../src/features/admin/UsersView.vue'
import AuditView from '../../src/features/admin/AuditView.vue'
import RecordFields from '../../src/features/admin/RecordFields.vue'
import ContentAccessPanel from '../../src/features/admin/ContentAccessPanel.vue'

const userId = '00000000-0000-4000-8000-000000000001'
const adminId = '00000000-0000-4000-8000-000000000002'
const user = { id: userId, account_normalized: '商家账号', nickname: null, role: 'user', status: 'active', auth_version: 0, profile_version: 'profile-v1', created_at: '2026-10-15T00:00:00Z', last_login_at: null, shop_name: null, category: null, email: null, phone: null, task_count: 0, available: 5, frozen: 0, consumed: 0 }
const admin = { ...user, id: adminId, account_normalized: '核查管理员', role: 'admin' }
const overlay = { props: ['open', 'title'], template: '<section v-if="open" :aria-label="title"><slot/><slot name="actions"/></section>' }
const global = { stubs: { AppDrawer: overlay, AppDialog: overlay, RouterLink: { template: '<a><slot/></a>' } } }
const wrappers: VueWrapper[] = []
const open = (component: Parameters<typeof mount>[0], props = {}) => { const wrapper = mount(component, { props, global }); wrappers.push(wrapper); return wrapper }
const click = (wrapper: VueWrapper, text: string) => wrapper.findAll('button').find(button => button.text() === text)!.trigger('click')
beforeEach(() => {
  vi.resetAllMocks()
  managed.restoreAdjustment.mockReturnValue(null)
  managed.listUsers.mockResolvedValue({ items: [user, admin], next_cursor: null, page: 1, page_size: 20, total: 2 })
  managed.getUser.mockResolvedValue(user)
  api.listUsers.mockResolvedValue({ items: [user, admin], next_cursor: null })
  api.usersSummary.mockResolvedValue(null)
  api.userAccount.mockResolvedValue({ available: 5, frozen: 0, consumed: 0, credited_total: 5 })
  api.userLedger.mockResolvedValue({ items: [], next_cursor: null })
  api.listAdminLedger.mockResolvedValue({ items: [], next_cursor: null })
  api.ledgerSummary.mockResolvedValue(null)
  api.auditSummary.mockResolvedValue(null)
  api.listContentGrants.mockResolvedValue({ items: [], next_cursor: null })
})
afterEach(() => wrappers.splice(0).forEach(wrapper => wrapper.unmount()))

it('shows accounts in user lists, details and credit adjustment recipients without UUID fallbacks', async () => {
  const users = open(UsersView); await flushPromises()
  expect(users.text()).toContain('商家账号'); expect(users.text()).not.toContain(userId)
  await click(users, '查看'); await flushPromises()
  expect(managed.getUser).toHaveBeenCalledWith(userId)
  expect(users.get('[aria-label="用户信息"]').text()).toContain('商家账号')
  expect(users.text()).not.toContain('用户编号'); expect(users.text()).not.toContain(userId)
  await click(users, '积分调整'); await flushPromises()
  expect(users.get('#admin-user-adjustment').text()).toContain('商家账号')
  expect(users.text()).not.toContain(userId)
})

it('retries a pending adjustment for an unlisted account without exposing its internal recipient', async () => {
  const missing = '00000000-0000-4000-8000-000000000099'
  const original = { user_id: missing, body: { delta: 5, reason: '试用', business_key: 'original-adjustment' } }
  managed.restoreAdjustment.mockReturnValue(original)
  managed.adjustCredits.mockResolvedValue({ ...original.body, user_id: missing, actor_id: 'admin-self-id', ledger_id: 'ledger-resource' })
  const wrapper = open(UsersView); await flushPromises()
  expect(wrapper.get('.pending-adjustment').text()).toContain('+5 积分 · 试用'); expect(wrapper.text()).not.toContain(missing)
  await click(wrapper, '重试原积分调整'); await flushPromises()
  expect(managed.adjustCredits).toHaveBeenCalledWith(original)
  expect(managed.forgetAdjustment).toHaveBeenCalledWith('admin-self-id', 'original-adjustment')
  expect(wrapper.find('.pending-adjustment').exists()).toBe(false)
  expect(wrapper.text()).not.toContain(missing)
})

it('hides nested identity fields while retaining resource identifiers and ledger data', () => {
  const wrapper = open(RecordFields, { value: { user_id: userId, actor_id: adminId, task_id: 'task-resource', ledger_id: 'ledger-resource', before: { owner: adminId, available: 5 }, after: [{ operator: adminId, old_owner: userId, amount: 8 }] } })
  expect(wrapper.text()).not.toContain(userId); expect(wrapper.text()).not.toContain(adminId)
  expect(wrapper.text()).toContain('task-resource'); expect(wrapper.text()).toContain('ledger-resource')
  expect(wrapper.text()).toContain('可用积分'); expect(wrapper.text()).toContain('8')
})

it('resolves audit actors and account-status objects to accounts, including details', async () => {
  api.listAudit.mockResolvedValue({ items: [{ id: 'audit-resource', actor_id: adminId, object_id: userId, action: 'account_status', reason: '状态变更', changes: { user_id: userId, status: 'disabled' }, created_at: '2026-10-15T00:00:00Z' }], next_cursor: null, page: 1, page_size: 20, total: 1 })
  const wrapper = open(AuditView); await flushPromises()
  expect(wrapper.text()).toContain('核查管理员')
  expect(wrapper.text()).not.toContain(userId); expect(wrapper.text()).not.toContain(adminId)
  await click(wrapper, '查看详情')
  expect(wrapper.text()).toContain('商家账号')
  expect(wrapper.text()).not.toContain(userId); expect(wrapper.text()).not.toContain(adminId)
  expect(wrapper.text()).toContain('停用')
})

it('selects authorization accounts by name but submits their internal IDs', async () => {
  api.createContentGrant.mockResolvedValue({})
  const wrapper = open(ContentAccessPanel)
  await click(wrapper, '查看授权与访问入口'); await flushPromises()
  await click(wrapper, '提交指定对象授权')
  const form = wrapper.get('#content-grant'), selects = form.findAll('select')
  expect(selects[0].text()).toContain('核查管理员')
  expect(form.text()).not.toContain(userId); expect(form.text()).not.toContain(adminId)
  await selects[0].setValue(adminId); await selects[1].setValue(userId)
  await form.get('input[type="text"]:not(.el-select__input)').setValue('task-resource')
  await form.get('input[type="datetime-local"]').setValue('2026-10-16T12:00')
  await form.get('textarea').setValue('核查授权')
  await form.trigger('submit'); await flushPromises()
  expect(api.createContentGrant).toHaveBeenCalledWith(expect.objectContaining({ actor_id: adminId, scope: { user_id: userId, resource_id: 'task-resource', resource_type: 'task' } }))
})
