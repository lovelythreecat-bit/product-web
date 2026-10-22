import { afterEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import UiInput from '../../src/components/ui/UiInput.vue'
import UiSelect from '../../src/components/ui/UiSelect.vue'
import UiButton from '../../src/components/ui/UiButton.vue'

afterEach(() => { document.body.innerHTML = '' })

it('offers every suggestion when reopening a filled field without changing its text', async () => {
  const Harness = defineComponent({ components: { UiInput }, setup: () => ({ value: ref('自然') }),
    template: '<UiInput v-model="value" :suggestions="[\'自然\', \'专业\', \'亲切\']" /><output>{{ value }}</output>' })
  const wrapper = mount(Harness, { attachTo: document.body })
  const input = wrapper.get('input')
  await flushPromises()
  ;(input.element as HTMLInputElement).focus()
  await vi.waitFor(() => expect(Array.from(document.querySelectorAll('[role="option"]'), item => item.textContent)).toEqual(['自然', '专业', '亲切']))
  expect(wrapper.get('output').text()).toBe('自然')
  wrapper.unmount()
})

it('reopens suggestions after choosing one while retaining typed filtering and custom input', async () => {
  const Harness = defineComponent({ components: { UiInput }, setup: () => ({ value: ref('') }),
    template: '<UiInput v-model="value" :suggestions="[\'自然\', \'专业\', \'亲切\']" /><output>{{ value }}</output>' })
  const wrapper = mount(Harness, { attachTo: document.body })
  const input = wrapper.get('input')
  await flushPromises()
  ;(input.element as HTMLInputElement).focus()
  await vi.waitFor(() => expect(document.querySelector('[role="option"]')?.textContent).toBe('自然'))
  ;(document.querySelector('[role="option"]') as HTMLElement).click()
  await flushPromises()
  expect(wrapper.get('output').text()).toBe('自然')
  await input.trigger('mousedown'); await input.trigger('click')
  await vi.waitFor(() => expect(Array.from(document.querySelectorAll('[role="option"]'), item => item.textContent)).toEqual(['自然', '专业', '亲切']))
  await input.setValue('专')
  await vi.waitFor(() => expect(Array.from(document.querySelectorAll('[role="option"]'), item => item.textContent)).toEqual(['专业']))
  await input.setValue('直接坦诚，保留商品事实')
  await vi.waitFor(() => expect(document.querySelectorAll('[role="option"]')).toHaveLength(0))
  expect(wrapper.get('output').text()).toBe('直接坦诚，保留商品事实')
  await input.trigger('click')
  await vi.waitFor(() => expect(Array.from(document.querySelectorAll('[role="option"]'), item => item.textContent)).toEqual(['自然', '专业', '亲切']))
  expect(wrapper.get('output').text()).toBe('直接坦诚，保留商品事实')
  wrapper.unmount()
})

it('freezes a selection with its parent fieldset and re-enables it after the pending action ends', async () => {
  const Harness = defineComponent({ components: { UiSelect }, props: { pending: Boolean }, setup: () => ({ value: ref('copy') }),
    template: '<fieldset :disabled="pending"><UiSelect v-model="value"><option value="copy">文案</option><option value="image">图片</option></UiSelect><output>{{ value }}</output></fieldset>' })
  const wrapper = mount(Harness, { props: { pending: true } })
  await flushPromises()
  await wrapper.get('select').setValue('image')
  expect(wrapper.get('output').text()).toBe('copy')
  expect(wrapper.find('.el-select__wrapper.is-disabled').exists()).toBe(true)
  await wrapper.setProps({ pending: false }); await flushPromises()
  await wrapper.get('select').setValue('image')
  expect(wrapper.get('output').text()).toBe('image')
  wrapper.unmount()
})

it('starts unfilled text fields empty and honors controlled value-only selections', async () => {
  const input = mount(UiInput)
  expect((input.get('input').element as HTMLInputElement).value).toBe('')
  const select = mount(UiSelect, { props: { value: 'image' }, slots: { default: '<option value="copy">文案</option><option value="image">图片</option>' } })
  await flushPromises()
  expect((select.get('select').element as HTMLSelectElement).value).toBe('image')
  expect(select.text()).toContain('图片')
  input.unmount(); select.unmount()
})

it('preserves numeric values, empty input and DOM input events used by existing forms', async () => {
  const wrapper = mount(UiInput, { props: { modelValue: 8, type: 'number' }, attrs: { id: 'price', min: 0, required: true } })
  const input = wrapper.get('input')
  expect(input.attributes('id')).toBe('price')
  expect((input.element as HTMLInputElement).checkValidity()).toBe(true)
  await input.setValue('12')
  expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([12])
  expect((wrapper.emitted('input')?.at(-1)?.[0] as Event).target).toBe(input.element)
  await input.setValue('')
  expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([''])
  await wrapper.setProps({ modelValue: '' })
  expect((input.element as HTMLInputElement).checkValidity()).toBe(false)
  wrapper.unmount()
})

it('retains boolean option values and rejects missing required selections in a native form', async () => {
  const Harness = defineComponent({ components: { UiSelect }, setup: () => ({ value: ref<string | boolean>('') }),
    template: '<form><label for="state">配置状态</label><UiSelect id="state" v-model="value" required><option value="" disabled>请选择</option><option :value="true">启用</option><option :value="false">停用</option></UiSelect><output>{{ typeof value }}:{{ value }}</output></form>' })
  const wrapper = mount(Harness, { attachTo: document.body })
  expect((wrapper.get('form').element as HTMLFormElement).checkValidity()).toBe(false)
  await wrapper.get('select').setValue('false')
  await flushPromises()
  expect(wrapper.get('output').text()).toBe('boolean:false')
  expect((wrapper.get('form').element as HTMLFormElement).checkValidity()).toBe(true)
  expect(wrapper.get('[role="combobox"]').attributes('id')).toBe('state')
  wrapper.unmount()
})

it('keeps footer buttons associated with their form and exposes focus for menus and confirmation dialogs', () => {
  const wrapper = mount(UiButton, { props: { type: 'submit' }, attrs: { form: 'edit-product', class: 'button primary' }, slots: { default: '保存' }, attachTo: document.body })
  expect(wrapper.get('button').attributes('type')).toBe('submit')
  expect(wrapper.get('button').attributes('form')).toBe('edit-product')
  wrapper.vm.focus()
  expect(document.activeElement).toBe(wrapper.get('button').element)
  wrapper.unmount()
})
