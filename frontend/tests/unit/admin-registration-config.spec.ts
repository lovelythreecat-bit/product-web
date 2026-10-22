import { expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
const api = vi.hoisted(() => ({ registrationConfig: vi.fn(), saveRegistrationConfig: vi.fn(), listAdminLedger: vi.fn() }))
const managed = vi.hoisted(() => ({ listUsers: vi.fn(), restoreAdjustment: vi.fn(() => null) }))
vi.mock('../../src/api/admin', () => api)
vi.mock('../../src/api/adminUsers', () => managed)
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: { value: 0 }, profile: { value: { user_id: 'admin' } } }, onIdentityChange: () => () => {} }))
import UsersView from '../../src/features/admin/UsersView.vue'
import CreditsView from '../../src/features/admin/CreditsView.vue'

it('user and credit lists do not load or expose the removed registration configuration', async () => {
 managed.listUsers.mockResolvedValue({ items: [], next_cursor: null })
 api.listAdminLedger.mockResolvedValue({ items: [], next_cursor: null })
 for (const component of [UsersView, CreditsView]) {
  const wrapper = mount(component, { global: { stubs: { AppDrawer: true, AppDialog: true } } })
  await flushPromises()
  expect(wrapper.text()).not.toContain('注册赠送配置')
  expect(wrapper.find('#registration-config').exists()).toBe(false)
  wrapper.unmount()
 }
 expect(api.registrationConfig).not.toHaveBeenCalled()
 expect(api.saveRegistrationConfig).not.toHaveBeenCalled()
})
