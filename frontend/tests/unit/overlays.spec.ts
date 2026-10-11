import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
const components = import.meta.glob('../../src/components/App{Dialog,Drawer}.vue')
describe('shared overlay contracts', () => {
  it('offers both dialog and drawer with labeled content and controlled visibility', async () => {
    expect(Object.keys(components), '缺少统一弹层组件').toHaveLength(2)
    for (const load of Object.values(components)) {
      const component = (await load() as { default: object }).default
      const wrapper = mount(component, { props: { open:false, title:'任务详情' }, slots: {default:'只读内容'} })
      expect(wrapper.find('dialog').exists()).toBe(true)
      expect(wrapper.find('dialog').attributes('aria-labelledby')).toBeTruthy()
      expect(wrapper.text()).toContain('只读内容')
      wrapper.unmount()
    }
  })
})