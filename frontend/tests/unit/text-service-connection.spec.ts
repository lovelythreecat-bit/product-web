import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { ApiError } from '../../src/api/client'

const api = vi.hoisted(() => ({ getTextServiceConnection: vi.fn(), saveTextServiceConnection: vi.fn() }))
vi.mock('../../src/api/admin', () => api)
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: { value: 0 } } }))
import TextServiceConnection from '../../src/features/admin/TextServiceConnection.vue'

const row = { base_url: 'http://127.0.0.1:8000', revision: 2, has_service_key: true, updated_at: null }
const global = { stubs: { AppDrawer: defineComponent({ props: ['open'], template: '<section v-if="open"><slot/><slot name="actions"/></section>' }) } }
beforeEach(() => { vi.clearAllMocks(); api.getTextServiceConnection.mockResolvedValue(row) })

it('keeps the service key write only and emits saved only after a successful response', async () => {
  const wrapper = mount(TextServiceConnection, { global }); await flushPromises()
  await wrapper.get('button').trigger('click')
  expect((wrapper.get('#text-service-key').element as HTMLInputElement).value).toBe('')
  expect(wrapper.find('#text-service-reason').exists()).toBe(false)
  api.saveTextServiceConnection.mockResolvedValue({ ...row, revision: 3 })
  await wrapper.get('form').trigger('submit'); await flushPromises()
  expect(api.saveTextServiceConnection).toHaveBeenCalledWith({ expected_revision: 2, base_url: row.base_url })
  expect(wrapper.emitted('saved')).toHaveLength(1)
  expect(wrapper.text()).toContain('服务连接已保存')
  wrapper.unmount()
})

it('retains a conflicting draft and requires an explicit reload', async () => {
  const wrapper = mount(TextServiceConnection, { global }); await flushPromises()
  await wrapper.get('button').trigger('click')
  await wrapper.get('#text-service-url').setValue('http://127.0.0.1:9000')
  await wrapper.get('#text-service-key').setValue('TEST_ONLY_replacement')
  api.saveTextServiceConnection.mockRejectedValue(new ApiError('连接已改变', 409))
  await wrapper.get('form').trigger('submit'); await flushPromises()
  expect(wrapper.emitted('saved')).toBeUndefined()
  expect((wrapper.get('#text-service-url').element as HTMLInputElement).value).toContain('9000')
  expect(wrapper.findAll('button').find(b => b.text() === '保存服务连接')!.attributes('disabled')).toBeDefined()
  api.getTextServiceConnection.mockResolvedValue({ ...row, revision: 3 })
  await wrapper.findAll('button').find(b => b.text() === '放弃草稿并载入最新连接')!.trigger('click')
  await flushPromises()
  expect((wrapper.get('#text-service-key').element as HTMLInputElement).value).toBe('')
  expect((wrapper.get('#text-service-url').element as HTMLInputElement).value).toBe(row.base_url)
  wrapper.unmount()
})
