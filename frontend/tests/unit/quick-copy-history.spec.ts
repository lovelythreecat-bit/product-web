import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import QuickGenerationView from '../../src/features/quick-generation/QuickGenerationView.vue'
import QuickCopyHistory from '../../src/features/quick-generation/QuickCopyHistory.vue'
import type { QuickView } from '../../src/api/quickGeneration'

const api = vi.hoisted(() => ({ getQuickRun: vi.fn(), saveQuickRun: vi.fn(), prepareQuickRun: vi.fn(), submitQuickBatch: vi.fn() }))
vi.mock('../../src/api/quickGeneration', () => api)
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { runId: 'copies' }, query: {} }), useRouter: () => ({ push: vi.fn() }), onBeforeRouteLeave: vi.fn(), onBeforeRouteUpdate: vi.fn() }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(1), refreshAccount: vi.fn().mockResolvedValue({}) } }))
vi.mock('../../src/api/catalog', () => ({ listAgents: vi.fn().mockResolvedValue([]), quote: vi.fn().mockResolvedValue({ credits: 10 }) }))
vi.mock('../../src/api/conversations', () => ({ getProductVersion: vi.fn().mockResolvedValue({ version: 'p1', product: { name: '杯子', category: '家居' } }) }))
vi.mock('../../src/api/works', () => ({ getWork: vi.fn(async (id: string) => ({ work_id: id, kind: 'copy', items: [{ file_id: id + '-file', text: id + '完整文案', media_type: 'text/plain' }] })) }))
const overlay = { props: ['open', 'title'], template: '<section v-if="open" role="dialog" :aria-label="title"><slot/><slot name="actions"/></section>' }
const options = { global: { stubs: { AppDialog: overlay, AppDrawer: overlay, QuickProductEditor: true, RouterLink: { template: '<a><slot/></a>' } } } }
function fixture(step = 2, single = false) {
  const item = (id: string, type: string) => ({ label: type, task_id: id, request: { input: { product_version: 'p1', product: { name: '杯子' }, material_versions: [], instruction: '', parameters: { copy_type: type } }, confirmed_quote: { credits: 10 } } })
  const title = item('title', '商品标题'), old = item('old-copy', '宣传文案'), latest = item('new-copy', '宣传文案'), failed = item('failed-copy', '宣传文案')
  const tasks = Object.fromEntries([title, old, latest, failed].map(entry => [entry.task_id, { agent_id: 'copy', input: entry.request.input, policy_versions: {}, task: { task_id: entry.task_id, state: entry === failed ? 'FAILED' : 'SUCCEEDED', settlement_state: entry === failed ? 'RELEASED' : 'CONSUMED', work_ids: [entry.task_id + '-work'], quote: { credits: 10 }, created_at: '2026-10-21T03:00:00Z' } }]))
  return { run_id: 'copies', version: 1, conversation_id: 'c1', state: { step, draft: { product_version: 'p1', material_versions: [], copy_parameters: {}, copy_types: single ? ['宣传文案'] : ['商品标题', '宣传文案'], copy_texts: { 商品标题: '标题', 宣传文案: '当前文案' }, copy_text: '当前文案', copy_instruction: '', image_platform: '', image_outputs: [], image_instruction: '', video_instruction: '', video_first_frame_file_id: '' }, current: { copy: 'latest', image: null, video: null }, confirmed_copy: '已确认完整文案', confirmed_images: null, pending_batch: null, batches: [
    { id: 'original', kind: 'copy', submitted: true, items: [title, old] },
    { id: 'duplicate', kind: 'copy', submitted: true, items: [title, old] },
    { id: 'failed', kind: 'copy', submitted: true, items: [failed] },
    { id: 'cancelled', kind: 'copy', submitted: false, items: [old] },
    { id: 'latest', kind: 'copy', submitted: true, items: single ? [latest] : [title, latest] },
  ] }, tasks }
}
beforeEach(() => { vi.clearAllMocks(); api.getQuickRun.mockResolvedValue(fixture()) })

it.each([[2, false], [2, true], [5, false]])('opens only successful previous copy versions at step %s (single %s), including after reload', async (step, single) => {
  api.getQuickRun.mockResolvedValue(fixture(Number(step), Boolean(single)))
  for (let reload = 0; reload < 2; reload++) {
    const view = mount(QuickGenerationView, options); await flushPromises()
    try {
      const entry = view.find('button[aria-label="宣传文案历史版本"]')
      expect(entry.exists()).toBe(true)
      await entry.trigger('click'); await flushPromises()
      const history = view.get('[role="dialog"][aria-label="宣传文案历史版本"]')
      expect(history.findAll('[data-task-id]').map(task => task.attributes('data-task-id'))).toEqual(['old-copy'])
      expect(history.text()).toContain('old-copy-work完整文案')
      expect(history.findAll('a[download]')).toHaveLength(1)
      expect(history.findAll('button').some(button => button.text().includes('重新生成'))).toBe(false)
      expect(history.findAll('button').some(button => button.text() === '复制文案')).toBe(true)
      expect(api.prepareQuickRun).not.toHaveBeenCalled()
      expect(api.submitQuickBatch).not.toHaveBeenCalled()
    } finally { view.unmount() }
  }
})

it('shows an empty history instead of listing the current copy', async () => {
  const view = mount(QuickGenerationView, options); await flushPromises()
  try {
    const entry = view.find('button[aria-label="商品标题历史版本"]')
    expect(entry.exists()).toBe(true)
    await entry.trigger('click'); await flushPromises()
    const history = view.get('[role="dialog"][aria-label="商品标题历史版本"]')
    expect(history.findAll('[data-task-id]')).toHaveLength(0)
    expect(history.text()).toContain('暂无历史版本')
  } finally { view.unmount() }
})

it('keeps history open on refreshed data and closes it when the selected task changes', async () => {
  const run = fixture() as unknown as QuickView
  const item = run.state.batches![4]!.items[1]!
  const view = mount(QuickCopyHistory, { ...options, props: { run, item, agents: [] } })
  try {
    await view.get('button').trigger('click'); await flushPromises()
    const refreshed = structuredClone(run)
    await view.setProps({ run: refreshed, item: refreshed.state.batches![4]!.items[1]! })
    expect(view.find('[role="dialog"]').exists()).toBe(true)
    await view.setProps({ item: { ...item, task_id: 'replacement' } })
    expect(view.find('[role="dialog"]').exists()).toBe(false)
  } finally { view.unmount() }
})

it('orders previous successes newest-first and excludes aliases of the current task', async () => {
  const value = fixture()
  const oldest = structuredClone(value.state.batches[0]!.items[1]!)
  oldest.task_id = 'oldest-copy'
  value.tasks[oldest.task_id] = structuredClone(value.tasks['old-copy']!)
  value.tasks[oldest.task_id]!.task.task_id = oldest.task_id
  value.state.batches.unshift({ id: 'first', kind: 'copy', submitted: true, items: [oldest] })
  value.tasks['failed-copy'] = structuredClone(value.tasks['new-copy']!)
  const run = value as unknown as QuickView
  const view = mount(QuickCopyHistory, { ...options, props: { run, item: run.state.batches![5]!.items[1]!, agents: [] } })
  try {
    await view.get('button').trigger('click'); await flushPromises()
    expect(view.findAll('[data-task-id]').map(task => task.attributes('data-task-id'))).toEqual(['old-copy', 'oldest-copy'])
    expect(view.findAll('.quick-copy-version > h3').map(heading => heading.text())).toEqual(['宣传文案 · 第 2 版', '宣传文案 · 第 1 版'])
  } finally { view.unmount() }
})
