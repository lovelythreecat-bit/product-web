import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import type { Schema } from '../../src/types/api'

const api = vi.hoisted(() => ({ preparePrompt: vi.fn() }))
vi.mock('../../src/api/assist', () => ({ preparePrompt: api.preparePrompt }))
import PromptEditor from '../../src/features/workspace/PromptEditor.vue'

const wrappers: VueWrapper[] = []
const request = { original: '原指令' } as Schema<'AssistRequest'>
const button = (wrapper: VueWrapper, name: string) => wrapper.findAll('button').find(item => item.text() === name)!
function render(props: Record<string, unknown> = {}) {
  const wrapper = mount(PromptEditor, { props: { modelValue: '原指令', request, ...props } })
  wrappers.push(wrapper)
  return wrapper
}
beforeEach(() => { vi.resetAllMocks() })
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()) })

it('connects each configured label to its own textarea', () => {
  const first = render({ textareaId: 'quick-copy-instruction' })
  const second = render({ textareaId: 'quick-image-instruction' })
  expect(first.get('label').attributes('for')).toBe('quick-copy-instruction')
  expect(first.get('textarea').attributes('id')).toBe('quick-copy-instruction')
  expect(second.get('label').attributes('for')).toBe('quick-image-instruction')
  expect(second.get('textarea').attributes('id')).toBe('quick-image-instruction')
})

it('disables assistance, editing and undo while preserving the current instruction', async () => {
  api.preparePrompt.mockResolvedValue({ proposed: '已完善指令', missing_facts: [] })
  const wrapper = render()
  await button(wrapper, 'AI 帮我完善').trigger('click'); await flushPromises()
  await wrapper.setProps({ modelValue: '已完善指令', disabled: true })
  expect(wrapper.get('textarea').attributes('disabled')).toBeDefined()
  expect(button(wrapper, 'AI 帮我完善').attributes('disabled')).toBeDefined()
  expect(button(wrapper, '撤回辅助，恢复原指令').attributes('disabled')).toBeDefined()
  await button(wrapper, '撤回辅助，恢复原指令').trigger('click')
  await wrapper.get('textarea').setValue('不应写入')
  expect(wrapper.emitted('update:modelValue')).toEqual([['已完善指令']])
})

it('discards an in-flight suggestion if the editor becomes disabled', async () => {
  let resolve!: (value: { proposed: string }) => void
  api.preparePrompt.mockImplementationOnce(() => new Promise(done => { resolve = done }))
  const wrapper = render()
  await button(wrapper, 'AI 帮我完善').trigger('click')
  await wrapper.setProps({ disabled: true })
  resolve({ proposed: '迟到的辅助' }); await flushPromises()
  expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  expect(wrapper.text()).not.toContain('撤回辅助')
})

it('limits typed input to the configured maximum length', async () => {
  const wrapper = render({ maxLength: 5 })
  expect(wrapper.get('textarea').attributes('maxlength')).toBe('5')
  await wrapper.get('textarea').setValue('1234567')
  expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['12345'])
})

it('rejects an oversized AI suggestion without replacing or truncating the original', async () => {
  api.preparePrompt.mockResolvedValue({ proposed: '123456', missing_facts: [] })
  const wrapper = render({ maxLength: 5 })
  await button(wrapper, 'AI 帮我完善').trigger('click'); await flushPromises()
  expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  expect(wrapper.get('textarea').element.value).toBe('原指令')
  expect(wrapper.get('[role="alert"]').text()).toContain('5')
  expect(wrapper.get('[role="alert"]').text()).toContain('原指令已保留')
  expect(wrapper.text()).not.toContain('撤回辅助')
})

it('keeps default IDs and unlimited input behavior for existing callers', async () => {
  const wrapper = render()
  expect(wrapper.get('label').attributes('for')).toBe('creation-instruction')
  expect(wrapper.get('textarea').attributes('id')).toBe('creation-instruction')
  expect(wrapper.get('textarea').attributes('maxlength')).toBeUndefined()
  await wrapper.get('textarea').setValue('123456')
  expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['123456'])
})
