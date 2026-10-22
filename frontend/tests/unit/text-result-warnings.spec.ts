import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import ResultViewer from '../../src/components/ResultViewer.vue'
import TextWarnings from '../../src/components/TextWarnings.vue'
import type { Schema } from '../../src/types/api'
const api = vi.hoisted(() => ({ getWork: vi.fn(), listWorks: vi.fn(), deleteWork: vi.fn() }))
vi.mock('../../src/api/works', () => api)
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('../../src/features/workspace/drafts', () => ({ setSourceDraft: vi.fn() }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: { value: 1 } } }))
import TaskCard from '../../src/components/TaskCard.vue'
import WorksView from '../../src/features/works/WorksView.vue'

const overlay = defineComponent({ props: ['open'], template: '<section v-if="open" role="dialog"><slot /></section>' })
const work = (warnings?: string[]) => ({ work_id: 'work', kind: 'copy', items: [{ file_id: 'file', text: '完整文案正文' }], ...(warnings ? { warnings } : {}) }) as Schema<'WorkView'>
afterEach(() => vi.unstubAllGlobals())

it('supersedes a historical delivery summary with the current best-candidate decision', () => {
  const prefix = 'taobao.main_image.default: '
  const wrapper = mount(TextWarnings, { props: { warnings: [
    prefix + '图片已保留为候选图，未通过审核，不属于成功交付',
    prefix + '已交付最佳可用候选 c0001（综合分：83）；原审核未通过',
  ] } })
  expect(wrapper.text()).not.toContain('不属于成功交付')
  expect(wrapper.text()).toContain('已交付最佳可用候选 c0001')
  expect(wrapper.text()).toContain('原审核未通过')
  wrapper.unmount()
})

it.each([false, true])('keeps saved warnings out of results and preview while copying only the original body (compact: %s)', async compact => {
  const writeText = vi.fn(async () => {})
  vi.stubGlobal('navigator', { clipboard: { writeText } })
  const wrapper = mount(ResultViewer, { props: { work: work(['材质待核实', '<b>优惠待核实</b>']), compact }, global: { stubs: { AppDialog: overlay } } })
  expect(wrapper.text()).not.toContain('待核实')
  await wrapper.findAll('button').find(button => button.text() === '复制文案')!.trigger('click')
  expect(writeText).toHaveBeenCalledWith('完整文案正文')
  await wrapper.findAll('button').find(button => button.text() === '预览')!.trigger('click')
  expect(wrapper.get('[role="dialog"]').text()).not.toContain('待核实')
  expect(wrapper.get('[role="dialog"] .copy-result').text()).toBe('完整文案正文')
  wrapper.unmount()
})

const source = { task: { task_id: 'task', work_ids: ['work'], state: 'SUCCEEDED', settlement_state: 'CONSUMED', quote: { credits: 8 } }, input: { product: {}, parameters: {}, instruction: '' }, policy_versions: {}, materials: [], ledger_ids: [] } as unknown as Schema<'TaskDetail'>

it.each(['copy', 'image'])('shows saved %s warnings only after opening the workspace task details, as plain text', async kind => {
  api.getWork.mockResolvedValue({ ...work(['材质待核实', '<b>优惠待核实</b>']), kind, source })
  const wrapper = mount(TaskCard, { props: { detail: source }, global: { stubs: { AppDrawer: overlay } } })
  await flushPromises()
  expect(wrapper.text()).not.toContain('待核实')
  await wrapper.findAll('button').find(button => button.text() === '任务详情')!.trigger('click')
  const notices = wrapper.get('[role="dialog"] [aria-label="待核实提示"]')
  expect(notices.text()).toContain('材质待核实')
  expect(notices.text()).toContain('<b>优惠待核实</b>')
  expect(notices.find('b').exists()).toBe(false)
  wrapper.unmount()
})

it.each(['copy', 'image'])('shows saved %s warnings only inside the works task details', async kind => {
  const saved = { ...work(['材质待核实']), kind, created_at: '2026-10-18T00:00:00Z', source }
  api.listWorks.mockResolvedValue({ items: [saved], next_cursor: null })
  api.getWork.mockResolvedValue(saved)
  const wrapper = mount(WorksView, { global: { stubs: { AppDrawer: overlay, RouterLink: { template: '<a><slot /></a>' } } } })
  await flushPromises()
  expect(wrapper.text()).not.toContain('待核实')
  await wrapper.findAll('button').find(button => button.text() === '任务详情')!.trigger('click')
  await flushPromises()
  expect(wrapper.get('[role="dialog"] [aria-label="待核实提示"]').text()).toContain('材质待核实')
  wrapper.unmount()
})

it.each([undefined, []])('omits warning decoration for historical or warning-free works (%s)', warnings => {
  const wrapper = mount(ResultViewer, { props: { work: work(warnings) }, global: { stubs: { AppDialog: overlay } } })
  expect(wrapper.find('[aria-label="待核实提示"]').exists()).toBe(false)
  expect(wrapper.get('.copy-result').text()).toBe('完整文案正文')
  wrapper.unmount()
})
