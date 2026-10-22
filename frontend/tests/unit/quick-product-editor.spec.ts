import { mount, flushPromises } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'
import QuickProductEditor from '../../src/features/quick-generation/QuickProductEditor.vue'
const api = vi.hoisted(() => ({ createProductVersion: vi.fn() }))
vi.mock('../../src/api/conversations', () => api)
it('edits product fields inline and waits for the workflow to persist before reporting success', async () => {
  let finish!: () => void
  const persist = vi.fn(() => new Promise<void>(resolve => { finish = resolve }))
  api.createProductVersion.mockResolvedValue({ version: 'v2', product: { name: '新商品', product_type: 'home' } })
  const editor = mount(QuickProductEditor, { props: {
    inline: true, open: true, ownerKey: 'run-a', requiredFields: [], persist,
    product: { product_id: 'p1', version: 'v1', created_at: '2026-10-18T00:00:00Z', product: { name: '旧商品', product_type: 'home' } },
  } })
  try {
    expect(editor.find('[role="dialog"]').exists()).toBe(false)
    await editor.get('input#quick-product-name').setValue('新商品')
    await editor.get('form').trigger('submit')
    await flushPromises()
    expect(persist).toHaveBeenCalled()
    expect(editor.emitted('saved')).toBeUndefined()
    finish(); await flushPromises()
    expect(editor.emitted('saved')?.[0]?.[0]).toMatchObject({ version: 'v2' })
  } finally { editor.unmount() }
})
it('discards an old product-save completion after the workflow changes', async () => {
  let resolve!: (value: unknown) => void
  api.createProductVersion.mockImplementation(() => new Promise(done => { resolve = done }))
  const editor = mount(QuickProductEditor, { props: { open: false, ownerKey: 'run-a', requiredFields: [], product: { product_id: 'p1', version: 'v1', created_at: '2026-10-18T00:00:00Z', product: { name: '旧商品', product_type: 'home' } } }, global: { stubs: { AppDrawer: { template: '<div><slot/><slot name="actions"/></div>' } } } })
  await editor.setProps({ open: true })
  await editor.get('form').trigger('submit')
  await editor.setProps({ open: false, ownerKey: 'run-b' })
  resolve({ version: 'old-save', product: { name: '旧商品' } }); await flushPromises()
  expect(editor.emitted('saved')).toBeUndefined()
  editor.unmount()
})
