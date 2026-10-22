import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import QuickProductSummary from '../../src/features/quick-generation/QuickProductSummary.vue'
import type { Schema } from '../../src/types/api'

const product: Schema<'ProductVersionView'> = { product_id: 'p1', version: 'v1', created_at: '2026-10-19T00:00:00Z', product: {
  name: '陶瓷杯', category: '日用器皿', product_type: 'home', brand: '示例品牌',
  material: '陶瓷', capacity: '350ml', description: '完整保留的商品说明\n第二行',
  custom_fact: '已有补充资料原文',
} }
function summary(overrides: { materials?: Schema<'FileVersionRef'>[]; readOnly?: boolean; disabled?: boolean; uploading?: boolean } = {}) {
  return mount(QuickProductSummary, { props: { product, materials: [], disabled: false, uploading: false, ...overrides } })
}

it('keeps every filled product fact visible across the summary groups, including legacy fields', () => {
  const view = summary()
  try {
    for (const value of ['陶瓷杯', '日用器皿', '家居日用', '示例品牌', '陶瓷', '350ml', '完整保留的商品说明\n第二行', '已有补充资料原文']) expect(view.text()).toContain(value)
    expect(view.findAll('.quick-product-facts')).toHaveLength(4)
    expect(view.findAll('dd')).toHaveLength(6)
    view.findAll('button').find(button => button.text() === '编辑资料')!.element.click()
    expect(view.emitted('edit')).toHaveLength(1)
  } finally { view.unmount() }
})

it('renders a current image and a thumbnail for every uploaded reference', () => {
  const view = summary({ materials: [{ file_id: 'image-1', version: 'v1' }, { file_id: 'image-2', version: 'v1' }] })
  try {
    expect(view.findAll('.quick-material img')).toHaveLength(2)
    expect(view.get('.quick-reference-feature img').attributes('src')).toContain('image-1')
    expect(view.find('.quick-product-information img').exists()).toBe(false)
  } finally { view.unmount() }
})

it('switches references, previews adjacent images and recovers when the current image is removed', async () => {
  const materials = [1, 2, 3].map(n => ({ file_id: `image-${n}`, version: 'v1' }))
  const view = summary({ materials })
  try {
    await view.get('[data-reference-index="1"]').trigger('click')
    expect(view.get('.quick-reference-feature img').attributes('src')).toContain('image-2')
    await view.get('.quick-reference-feature').trigger('click')
    expect(view.get('[data-reference-preview]').attributes('src')).toContain('image-2')
    await view.get('[data-reference-next]').trigger('click')
    expect(view.get('[data-reference-preview]').attributes('src')).toContain('image-3')
    await view.setProps({ materials: materials.slice(0, 2) })
    expect(view.get('[data-reference-preview]').attributes('src')).toContain('image-2')
    await view.setProps({ materials: [] })
    expect(view.find('[data-reference-preview]').exists()).toBe(false)
  } finally { view.unmount() }
})

it('accepts multiple dragged image files in their original order', async () => {
  const view = summary()
  const files = [new File(['one'], 'front.png', { type: 'image/png' }), new File(['two'], 'side.webp', { type: 'image/webp' })]
  try {
    await view.get('.quick-product-references').trigger('drop', { dataTransfer: { files } })
    expect(view.emitted('dropFiles')).toEqual([[files]])
    expect(view.find('[role="alert"]').exists()).toBe(false)
  } finally { view.unmount() }
})

it('rejects unsupported files and uploads exceeding the remaining image slots', async () => {
  const view = summary({ materials: Array.from({ length: 3 }, (_, index) => ({ file_id: `image-${index}`, version: 'v1' })) })
  const image = new File(['image'], 'product.jpg', { type: 'image/jpeg' })
  try {
    await view.get('.quick-product-references').trigger('drop', { dataTransfer: { files: [new File(['pdf'], 'notes.pdf', { type: 'application/pdf' })] } })
    expect(view.get('[role="alert"]').text()).toContain('PNG、JPG 或 WebP')
    expect(view.emitted('dropFiles')).toBeUndefined()
    await view.get('.quick-product-references').trigger('drop', { dataTransfer: { files: [image, image] } })
    expect(view.get('[role="alert"]').text()).toContain('还可以添加 1 张')
    expect(view.emitted('dropFiles')).toBeUndefined()
    await view.get('.quick-product-references').trigger('drop', { dataTransfer: { files: [image] } })
    expect(view.emitted('dropFiles')).toEqual([[[image]]])
    expect(view.find('[role="alert"]').exists()).toBe(false)
  } finally { view.unmount() }
})

it('does not accept dropped files when read-only, disabled, uploading, or full', async () => {
  const files = [new File(['image'], 'product.png', { type: 'image/png' })]
  for (const overrides of [{ readOnly: true }, { disabled: true }, { uploading: true }, { materials: Array.from({ length: 4 }, (_, index) => ({ file_id: `image-${index}`, version: 'v1' })) }]) {
    const view = summary(overrides)
    try {
      await view.get('.quick-product-references').trigger('drop', { dataTransfer: { files } })
      expect(view.emitted('dropFiles')).toBeUndefined()
    } finally { view.unmount() }
  }
})

it('keeps all legacy references viewable without permitting another upload', async () => {
  const materials = Array.from({ length: 5 }, (_, index) => ({ file_id: `legacy-${index}`, version: 'v1' }))
  const view = summary({ materials })
  try {
    expect(view.findAll('.quick-material img')).toHaveLength(5)
    expect(view.get('.quick-upload').element.matches(':disabled')).toBe(true)
    await view.get('[data-reference-index="4"]').trigger('click')
    await view.get('.quick-reference-feature').trigger('click')
    expect(view.get('[data-reference-preview]').attributes('src')).toContain('legacy-4')
    expect(materials).toHaveLength(5)
  } finally { view.unmount() }
})
