import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const api = vi.hoisted(() => ({ listWorks: vi.fn(), getWork: vi.fn(), deleteWork: vi.fn() }))
vi.mock('../../src/api/works', () => api)
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: { value: 1 } } }))
vi.mock('../../src/features/workspace/drafts', () => ({ setSourceDraft: vi.fn() }))
import WorksView from '../../src/features/works/WorksView.vue'
import ResultViewer from '../../src/components/ResultViewer.vue'

const work = (id: string) => ({ work_id: id, task_id: 'task-' + id, conversation_id: 'conversation-1', kind: 'copy', name: id, created_at: '2026-10-18T00:00:00Z', items: [] })
const global = { stubs: { ResultViewer: { template: '<div><slot name="actions" /></div>' }, RouterLink: { template: '<a><slot /></a>' } } }
const resultPage = (ids: string[], page = 1, total = 24) => ({ items: ids.map(work), next_cursor: null, page, total, page_size: 10 })
beforeEach(() => { vi.clearAllMocks(); api.listWorks.mockResolvedValue(resultPage(['first'])) })

it('requests a numbered page and replaces the previous cards instead of appending', async () => {
  api.listWorks.mockResolvedValueOnce(resultPage(['first'])).mockResolvedValueOnce(resultPage(['second'], 2))
  const wrapper = mount(WorksView, { global }); await flushPromises()
  expect(api.listWorks).toHaveBeenLastCalledWith({ kind: undefined, q: undefined, page: 1, limit: 10 })
  wrapper.findComponent({ name: 'ElPagination' }).vm.$emit('current-change', 2); await flushPromises()
  expect(api.listWorks).toHaveBeenLastCalledWith({ kind: undefined, q: undefined, page: 2, limit: 10 })
  expect(wrapper.findAll('[data-work-id]').map(card => card.attributes('data-work-id'))).toEqual(['second'])
  expect(wrapper.findComponent({ name: 'ElPagination' }).props('total')).toBe(24)
  wrapper.unmount()
})

it('searches on submit, resets the page, and clears the search explicitly', async () => {
  const wrapper = mount(WorksView, { global }); await flushPromises()
  wrapper.findComponent({ name: 'ElPagination' }).vm.$emit('current-change', 2); await flushPromises()
  await wrapper.get('#works-query').setValue('  保温杯  ')
  expect(api.listWorks).toHaveBeenCalledTimes(2)
  await wrapper.get('form').trigger('submit'); await flushPromises()
  expect(api.listWorks).toHaveBeenLastCalledWith({ kind: undefined, q: '保温杯', page: 1, limit: 10 })
  await wrapper.findAll('button').find(button => button.text() === '重置')!.trigger('click'); await flushPromises()
  expect(api.listWorks).toHaveBeenLastCalledWith({ kind: undefined, q: undefined, page: 1, limit: 10 })
  wrapper.unmount()
})

it('discards an older page response when the type filter finishes first', async () => {
  let finish!: (value: unknown) => void
  api.listWorks.mockResolvedValueOnce(resultPage(['first'])).mockImplementationOnce(() => new Promise(resolve => { finish = resolve })).mockResolvedValueOnce(resultPage(['image-only']))
  const wrapper = mount(WorksView, { global }); await flushPromises()
  wrapper.findComponent({ name: 'ElPagination' }).vm.$emit('current-change', 2)
  await wrapper.findAll('button').find(button => button.text() === '图片')!.trigger('click'); await flushPromises()
  finish(resultPage(['stale'], 2)); await flushPromises()
  expect(api.listWorks).toHaveBeenLastCalledWith({ kind: 'image', q: undefined, page: 1, limit: 10 })
  expect(wrapper.findAll('[data-work-id]').map(card => card.attributes('data-work-id'))).toEqual(['image-only'])
  wrapper.unmount()
})

it('retains the visible page on failure and retries the requested page', async () => {
  api.listWorks.mockResolvedValueOnce(resultPage(['first'])).mockRejectedValueOnce(Error('offline')).mockResolvedValueOnce(resultPage(['second'], 2))
  const wrapper = mount(WorksView, { global }); await flushPromises()
  wrapper.findComponent({ name: 'ElPagination' }).vm.$emit('current-change', 2); await flushPromises()
  expect(wrapper.find('[data-work-id="first"]').exists()).toBe(true)
  await wrapper.findAll('button').find(button => button.text() === '重试加载')!.trigger('click'); await flushPromises()
  expect(api.listWorks).toHaveBeenLastCalledWith({ kind: undefined, q: undefined, page: 2, limit: 10 })
  expect(wrapper.findAll('[data-work-id]').map(card => card.attributes('data-work-id'))).toEqual(['second'])
  wrapper.unmount()
})

it('uses the server corrected page after deleting the last work on a page', async () => {
  api.listWorks.mockResolvedValueOnce(resultPage(['first'], 2, 11)).mockResolvedValueOnce(resultPage(['remaining'], 1, 10))
  api.getWork.mockResolvedValue({ ...work('first'), source: { policy_versions: { 'D-09': 'delete-v1' } } })
  const wrapper = mount(WorksView, { global }); await flushPromises()
  await wrapper.findAll('button').find(button => button.text() === '删除作品')!.trigger('click'); await flushPromises()
  await wrapper.findAll('button').find(button => button.text() === '确认删除')!.trigger('click'); await flushPromises()
  expect(api.listWorks).toHaveBeenLastCalledWith({ kind: undefined, q: undefined, page: 2, limit: 10 })
  expect(wrapper.findComponent({ name: 'ElPagination' }).props('currentPage')).toBe(1)
  expect(wrapper.find('[data-work-id="remaining"]').exists()).toBe(true)
  wrapper.unmount()
})

it('exposes deletion with confirmation and points the source link to the exact task', async () => {
  api.listWorks.mockResolvedValue({ items: [work('first')], next_cursor: null })
  api.getWork.mockResolvedValue({ ...work('first'), source: { policy_versions: { 'D-09': 'delete-v1' } } })
  const wrapper = mount(WorksView, { global }); await flushPromises()
  const card = wrapper.get('[data-work-id="first"]')
  expect(card.find('details').exists()).toBe(false)
  expect(card.text()).not.toContain('重新生成')
  expect(wrapper.find('h1').exists()).toBe(false)
  const source = card.get('.work-origin a')
  expect(source.attributes('to')).toBe('/workspace/conversation-1?task=task-first')
  expect(source.text()).toContain('来源任务')
  await card.findAll('button').find(button => button.text() === '删除作品')!.trigger('click'); await flushPromises()
  expect(api.deleteWork).not.toHaveBeenCalled()
  await wrapper.findAll('button').find(button => button.text() === '确认删除')!.trigger('click'); await flushPromises()
  expect(api.deleteWork).toHaveBeenCalledWith('first', { policy_version: 'delete-v1' })
  wrapper.unmount()
})

it('keeps copy and task actions on copy cards while reserving preview and downloads for media', async () => {
  const writeText = vi.fn(async () => {})
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
  api.listWorks.mockResolvedValue({ items: [
    { ...work('copy'), items: [{ file_id: 'copy-file', text: '完整文案\n最后一行' }] },
    { ...work('image'), kind: 'image', items: [1, 2, 3].map(n => ({ file_id: 'image-' + n })) },
    { ...work('video'), kind: 'video', items: [{ file_id: 'video-file' }] },
  ], next_cursor: null })
  const wrapper = mount(WorksView, { global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } } }); await flushPromises()
  const copy = wrapper.get('[data-work-id="copy"]')
  expect(copy.text()).not.toContain('预览')
  expect(copy.find('[download]').exists()).toBe(false)
  expect(copy.text()).toContain('任务详情')
  expect(copy.text()).toContain('删除作品')
  await copy.findAll('button').find(button => button.text() === '复制文案')!.trigger('click')
  expect(writeText).toHaveBeenCalledWith('完整文案\n最后一行')
  for (const id of ['image', 'video']) {
    const card = wrapper.get(`[data-work-id="${id}"]`)
    expect(card.text()).toContain('预览')
    expect(card.find('[download], [aria-haspopup="menu"]').exists()).toBe(true)
  }
  expect(wrapper.get('[data-work-id="image"] .result-body').findAll('img')).toHaveLength(3)
  expect(wrapper.findAllComponents(ResultViewer).every(viewer => viewer.props('galleryLayout'))).toBe(true)
  wrapper.unmount()
})

it('groups gallery downloads and downloads every file once with distinct filenames', async () => {
  const imageWork = { ...work('details'), message_id: 'message-details', kind: 'image' as const, items: [1, 2, 3].map(n => ({ file_id: 'image-' + n, text: null, actual_bytes: 100, content_url: `/api/v1/files/image-${n}/content`, file_version: 'v1', item_key: String(n), media_type: 'image/png' })) }
  const wrapper = mount(ResultViewer, { props: { work: imageWork, galleryLayout: true } })
  const downloads: { href: string | null; filename: string }[] = []
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
    downloads.push({ href: this.getAttribute('href'), filename: this.download })
  })
  try {
    expect(wrapper.get('.result-actions').findAll('a[download]')).toHaveLength(0)
    expect(wrapper.get('.result-actions').findAll('button').map(button => button.text())).toEqual(['预览', '下载'])
    const dropdown = wrapper.getComponent({ name: 'ElDropdown' })
    dropdown.vm.$emit('command', 1)
    expect(downloads).toEqual([{ href: '/api/v1/files/image-2/content', filename: 'details-2.png' }])
    downloads.length = 0
    dropdown.vm.$emit('command', 'all')
    expect(downloads).toEqual([1, 2, 3].map(n => ({ href: `/api/v1/files/image-${n}/content`, filename: `details-${n}.png` })))
  } finally { click.mockRestore(); wrapper.unmount() }
})
