import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TextChoices from '../../src/features/workspace/TextChoices.vue'
import { textParameters, validateTextParameters } from '../../src/features/workspace/textParameters'

describe('text writing requirements', () => {
  it('uses the product audience without exposing a second audience field', () => {
    const wrapper = mount(TextChoices, { props: { modelValue: { audience: '历史目标人群' } } })
    expect(wrapper.find('[aria-label="目标人群"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('目标人群')
    wrapper.unmount()
  })
  it('keeps custom scenarios and an integer limit in the outgoing task input', () => {
    expect(textParameters({ copy_type: '选购指南', platform: '品牌社群', audience: '新手',
      tone: '直接坦诚', max_chars: 120, extra_instructions: '先讲适用场景', output_type: 'main_image' })).toEqual({
      copy_type: '选购指南', platform: '品牌社群', audience: '新手', tone: '直接坦诚',
      max_chars: 120, extra_instructions: '先讲适用场景',
    })
    expect(textParameters({ max_chars: '', tone: '', copy_type: undefined })).toEqual({})
    expect(validateTextParameters({})).toBe('')
  })

  it.each([0, -1, 1.5, true, '120', NaN, Infinity, Number.MAX_SAFE_INTEGER + 1])(
    'rejects an invalid maximum instead of dropping the limit: %s', value => {
      expect(validateTextParameters({ max_chars: value })).toContain('正整数')
      expect(textParameters({ max_chars: value }).max_chars).toBe(value)
    },
  )

  it('accepts a positive integer and reports malformed string requirements', () => {
    expect(validateTextParameters({ max_chars: 120, copy_type: '自定义文案' })).toBe('')
    expect(validateTextParameters({ audience: false })).not.toBe('')
  })

  it('lets users type custom options and keeps other fields when editing', async () => {
    const wrapper = mount(TextChoices, { props: { modelValue: { tone: '自然', audience: '通勤者' } } })
    await wrapper.get('input[aria-label="文案类型"]').setValue('品牌故事')
    expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toEqual({
      tone: '自然', audience: '通勤者', copy_type: '品牌故事',
    })
    await wrapper.get('input[aria-label="最大字符数"]').setValue('120')
    expect(wrapper.emitted('update:modelValue')?.[1]?.[0]).toEqual({
      tone: '自然', audience: '通勤者', max_chars: 120,
    })
    await wrapper.setProps({ modelValue: { max_chars: 120, audience: '通勤者' } })
    await wrapper.get('input[aria-label="最大字符数"]').setValue('')
    expect(wrapper.emitted('update:modelValue')?.[2]?.[0]).toEqual({ audience: '通勤者' })
  })

  it('associates an invalid limit with a visible field error', () => {
    const wrapper = mount(TextChoices, { props: { modelValue: { max_chars: 0 } } })
    const input = wrapper.get('input[aria-label="最大字符数"]')
    expect(input.attributes('aria-invalid')).toBe('true')
    expect(wrapper.get('[role="alert"]').text()).toContain('正整数')
    expect(input.attributes('aria-describedby')).toContain(wrapper.get('[role="alert"]').attributes('id'))
  })
})
