import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'
const mocks = vi.hoisted(() => ({ changePassword: vi.fn(), replace: vi.fn() }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(1), changePassword: mocks.changePassword } }))
vi.mock('vue-router', () => ({ useRouter: () => ({ replace: mocks.replace }) }))
import ChangePasswordDrawer from '../../src/features/account/ChangePasswordDrawer.vue'
const wrappers: VueWrapper[] = []
afterEach(() => { wrappers.splice(0).forEach(w => w.unmount()); vi.resetAllMocks() })
const overlay = { props: ['open'], emits: ['update:open'], template: '<div v-if="open"><slot/><button @click="$emit(\'update:open\', false)">取消</button><slot name="actions"/></div>' }
function create() { const w = mount(ChangePasswordDrawer, { props: { open: true }, global: { stubs: { AppDrawer: overlay } } }); wrappers.push(w); return w }
async function fill(w: VueWrapper, confirmation = 'new-password-123') {
  await w.get('#current-password').setValue('old-password-123')
  await w.get('#new-password').setValue('new-password-123')
  await w.get('#confirm-password').setValue(confirmation)
}
it('blocks mismatching confirmation, keeps errors local, and redirects after successful change', async () => {
  const w = create(); await fill(w, 'mismatch'); await w.get('form').trigger('submit')
  expect(mocks.changePassword).not.toHaveBeenCalled(); expect(w.text()).toContain('两次密码不一致')
  await fill(w); mocks.changePassword.mockRejectedValueOnce(new Error('network'))
  await w.get('form').trigger('submit'); await flushPromises()
  expect(mocks.replace).not.toHaveBeenCalled(); expect(w.text()).toContain('修改未完成')
  mocks.changePassword.mockResolvedValue(true); await w.get('form').trigger('submit'); await flushPromises()
  expect(mocks.changePassword).toHaveBeenLastCalledWith({ current_password: 'old-password-123', new_password: 'new-password-123' })
  expect(mocks.replace).toHaveBeenCalledWith({ path: '/login', query: { passwordChanged: '1' } })
})
it('clears passwords when closed and blocks weak passwords', async () => {
  const w = create(); await fill(w); await w.get('#new-password').setValue('short'); await w.get('form').trigger('submit')
  expect(mocks.changePassword).not.toHaveBeenCalled(); expect(w.text()).toContain('10–128')
  await w.setProps({ open: false }); await w.setProps({ open: true })
  expect((w.get('#current-password').element as HTMLInputElement).value).toBe('')
  expect((w.get('#new-password').element as HTMLInputElement).value).toBe('')
})
