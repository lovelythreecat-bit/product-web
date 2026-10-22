import { flushPromises, mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import type { Component } from 'vue'
import { ElDialog } from 'element-plus/es/components/dialog/index'
const components = import.meta.glob('../../src/components/App{Dialog,Drawer}.vue')
describe('shared overlay contracts', () => {
  it('allows a read-only drawer without footer while retaining its explicit header close', async () => {
    const component = (await components['../../src/components/AppDrawer.vue']!() as { default: Component }).default
    const wrapper = mount(component, { props: { open: true, title: '原任务诊断', showFooter: false }, attachTo: document.body, global: { stubs: { AppDialog: false, AppDrawer: false } } })
    await flushPromises()
    expect(document.querySelector('.overlay-actions')).toBeNull()
    const close = document.querySelector<HTMLButtonElement>('.overlay-header button[aria-label="关闭"]')!
    expect(close).not.toBeNull()
    close.click(); await flushPromises()
    expect(wrapper.emitted('update:open')?.at(-1)).toEqual([false])
    wrapper.unmount(); await flushPromises(); document.body.innerHTML = ''
  })
  it('keeps dialogs open on Escape and backdrop clicks, and closes through explicit controls', async () => {
    const component = (await components['../../src/components/AppDialog.vue']!() as { default: Component }).default
    const wrapper = mount(component, { props: { open: true, title: '确认生成', purpose: 'charge' }, attachTo: document.body, global: { stubs: { AppDialog: false, AppDrawer: false } } })
    await flushPromises()
    expect(wrapper.getComponent(ElDialog).props('closeOnPressEscape')).toBe(false)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }))
    await flushPromises()
    document.querySelector<HTMLElement>('.el-overlay-dialog')?.click()
    await flushPromises()
    expect(wrapper.emitted('update:open')).toBeUndefined()
    const cancel = Array.from(document.querySelectorAll<HTMLButtonElement>('.overlay-actions button')).find(button => button.textContent?.trim() === '取消')!
    cancel.click()
    await flushPromises()
    expect(wrapper.emitted('update:open')?.at(-1)).toEqual([false])
    wrapper.unmount()
    await flushPromises()
    document.body.innerHTML = ''
  })
  it('offers both dialog and drawer with labeled content and controlled visibility', async () => {
    expect(Object.keys(components), '缺少统一弹层组件').toHaveLength(2)
    for (const load of Object.values(components)) {
      const component = (await load() as { default: Component }).default
      const wrapper = mount(component, { props: { open:false, title:'任务详情' }, slots: {default:'只读内容'}, attachTo: document.body, global: { stubs: { AppDialog: false, AppDrawer: false } } })
      expect(document.querySelector('.app-overlay')?.textContent ?? '').not.toContain('只读内容')
      await wrapper.setProps({ open: true }); await flushPromises()
      const dialog = document.querySelector('.app-overlay')!
      expect(dialog.getAttribute('aria-labelledby')).toBeTruthy()
      expect(dialog.textContent).toContain('只读内容')
      const close = Array.from(dialog.querySelectorAll('button')).find(button => button.textContent?.trim() === '关闭')!
      close.click(); await flushPromises()
      expect(wrapper.emitted('update:open')?.at(-1)).toEqual([false])
      await wrapper.setProps({ open: false }); await flushPromises()
      wrapper.unmount()
      await flushPromises()
      document.body.innerHTML = ''
    }
  })
})
