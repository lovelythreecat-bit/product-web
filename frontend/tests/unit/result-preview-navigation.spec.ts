import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ResultViewer from '../../src/components/ResultViewer.vue'
import type { Schema } from '../../src/types/api'

it.each([false, true])('opens the selected image and allows keyboard navigation through all three detail images (gallery: %s)', async galleryLayout => {
  const work = { work_id: 'details', kind: 'image', items: [1, 2, 3].map(n => ({ file_id: 'image-' + n })) } as Schema<'WorkView'>
  const wrapper = mount(ResultViewer, { props: { work, galleryLayout }, global: { stubs: { AppDialog: { props: ['open'], template: '<div v-if="open" role="dialog"><slot /></div>' } } } })
  await wrapper.findAll('.result-item>img')[1].trigger('click')
  expect(wrapper.get('[role="dialog"] img').attributes('src')).toContain('image-2')
  expect(wrapper.findAll('[role="dialog"] img')).toHaveLength(1)
  await wrapper.get('[data-preview-next]').trigger('click')
  expect(wrapper.get('[role="dialog"] img').attributes('src')).toContain('image-3')
  await wrapper.get('.preview-gallery').trigger('keydown', { key: 'ArrowLeft' })
  expect(wrapper.get('[role="dialog"] img').attributes('src')).toContain('image-2')
  expect(wrapper.get('[aria-live="polite"]').text()).toContain('2 / 3')
  wrapper.unmount()
})
