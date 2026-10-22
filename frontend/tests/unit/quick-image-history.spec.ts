import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import QuickGenerationView from '../../src/features/quick-generation/QuickGenerationView.vue'
import QuickImageHistory from '../../src/features/quick-generation/QuickImageHistory.vue'
import type { QuickView } from '../../src/api/quickGeneration'

const api = vi.hoisted(() => ({ getQuickRun: vi.fn(), saveQuickRun: vi.fn(), prepareQuickRun: vi.fn(), submitQuickBatch: vi.fn() }))
vi.mock('../../src/api/quickGeneration', () => api)
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { runId: 'images' }, query: {} }), useRouter: () => ({ push: vi.fn() }), onBeforeRouteLeave: vi.fn(), onBeforeRouteUpdate: vi.fn() }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(1), refreshAccount: vi.fn() } }))
vi.mock('../../src/api/catalog', () => ({ listAgents: vi.fn().mockResolvedValue([]), quote: vi.fn().mockResolvedValue({ credits: 20 }) }))
vi.mock('../../src/api/conversations', () => ({ getProductVersion: vi.fn().mockResolvedValue({ version: 'p1', product: { name: '杯子', category: '家居' } }) }))
vi.mock('../../src/api/works', () => ({ getWork: vi.fn(async (id: string) => ({ work_id: id, kind: 'image', items: Array.from({ length: id.includes('details') ? 3 : 1 }, (_, i) => ({ file_id: `${id}-${i}`, media_type: 'image/png' })) })) }))
const overlay = { props: ['open', 'title'], template: '<section v-if="open" role="dialog" :aria-label="title"><slot/><slot name="actions"/></section>' }
const options = { global: { stubs: { AppDialog: overlay, AppDrawer: overlay, QuickProductEditor: true, RouterLink: { template: '<a><slot/></a>' } } } }
function fixture(step = 3, used = 1) {
  const input = { product_version: 'p1', product: { name: '杯子', category: '家居' }, material_versions: [], instruction: '', parameters: {} }
  const item = (id: string, output: string) => ({ label: output === 'main_image' ? '商品主图' : '详情图', task_id: id, free_regenerations_used: used, request: { input: { ...input, parameters: { output_type: output } }, confirmed_quote: { credits: 20 } } })
  const main = item('main', 'main_image'), old = item('old-details', 'detail_page'), latest = item('new-details', 'detail_page')
  const tasks = Object.fromEntries([main, old, latest].map(item => [item.task_id, { agent_id: 'image', input: item.request.input, policy_versions: {}, task: { task_id: item.task_id, state: 'SUCCEEDED', settlement_state: 'CONSUMED', work_ids: [item.task_id + '-work'], quote: { credits: 20 }, created_at: '2026-10-21T03:00:00Z' } }]))
  return { run_id: 'images', version: 1, conversation_id: 'c1', state: { step, draft: { product_version: 'p1', material_versions: [], copy_parameters: {}, copy_types: [], copy_texts: {}, copy_text: '', copy_instruction: '', image_platform: 'taobao', image_outputs: ['main_image', 'detail_page'], image_instruction: '', video_instruction: '', video_first_frame_file_id: '' }, current: { copy: null, image: 'latest', video: null }, confirmed_copy: '文案', confirmed_images: null, pending_batch: null, batches: [
    { id: 'original', kind: 'image', submitted: true, items: [main, old] },
    { id: 'cancelled', kind: 'image', submitted: false, items: [main, { ...old, task_id: null }] },
    { id: 'latest', kind: 'image', submitted: true, items: [main, latest] },
  ] }, tasks }
}
beforeEach(() => { vi.clearAllMocks(); api.getQuickRun.mockResolvedValue(fixture()) })

it.each([3, 5])('opens only previous versions of the selected image type at step %s and after reload', async step => {
  api.getQuickRun.mockResolvedValue(fixture(step))
  for (let reload = 0; reload < 2; reload++) {
    const view = mount(QuickGenerationView, options); await flushPromises()
    try {
      const entry = view.findAll('button').find(button => button.attributes('aria-label') === '详情图历史版本')
      expect(entry, 'each image type must have its own history entry').toBeDefined()
      await entry!.trigger('click'); await flushPromises()
      const history = view.get('[aria-label="详情图历史版本"][role="dialog"]')
      expect(history.findAll('[data-task-id]').map(task => task.attributes('data-task-id'))).toEqual(['old-details'])
      expect(history.findAll('a[download]')).toHaveLength(3)
      expect(history.findAll('button').some(button => button.text().includes('重新生成'))).toBe(false)
      await history.findAll('button').find(button => button.text() === '预览')!.trigger('click')
      expect(history.find('[aria-label="作品预览"] img').exists()).toBe(true)
      expect(api.prepareQuickRun).not.toHaveBeenCalled()
    } finally { view.unmount() }
  }
})

it('does not list the current image as history when it has never been regenerated', async () => {
  const view = mount(QuickGenerationView, options); await flushPromises()
  try {
    await view.get('button[aria-label="商品主图历史版本"]').trigger('click'); await flushPromises()
    const history = view.get('[role="dialog"][aria-label="商品主图历史版本"]')
    expect(history.findAll('[data-task-id]')).toHaveLength(0)
    expect(history.text()).toContain('暂无历史版本')
  } finally { view.unmount() }
})

it('keeps older versions newest-first without duplicates, cancelled batches or failed attempts', async () => {
  const value = fixture()
  const oldest = structuredClone(value.state.batches[0]!.items[1]!)
  oldest.task_id = 'oldest-details'
  value.tasks[oldest.task_id] = structuredClone(value.tasks['old-details']!)
  value.tasks[oldest.task_id]!.task.task_id = oldest.task_id
  value.state.batches.unshift({ id: 'first', kind: 'image', submitted: true, items: [oldest] })
  value.state.batches.splice(2, 0, structuredClone(value.state.batches[1]!))
  // A failed current regeneration must still expose all earlier successes.
  value.tasks['new-details']!.task.state = 'FAILED'
  api.getQuickRun.mockResolvedValue(value)
  const view = mount(QuickGenerationView, options); await flushPromises()
  try {
    await view.get('button[aria-label="详情图历史版本"]').trigger('click'); await flushPromises()
    const history = view.get('[role="dialog"][aria-label="详情图历史版本"]')
    expect(history.findAll('[data-task-id]').map(task => task.attributes('data-task-id'))).toEqual(['old-details', 'oldest-details'])
  } finally { view.unmount() }
})

it('keeps history open during polling and closes it when the selected task changes', async () => {
  const run = fixture() as unknown as QuickView
  const item = run.state.batches![2]!.items[1]!
  const view = mount(QuickImageHistory, { ...options, props: { run, item, agents: [] } })
  try {
    await view.get('button').trigger('click'); await flushPromises()
    const refreshed = structuredClone(run)
    await view.setProps({ run: refreshed, item: refreshed.state.batches![2]!.items[1]! })
    expect(view.find('[role="dialog"]').exists()).toBe(true)
    await view.setProps({ item: { ...item, task_id: 'replacement' } })
    expect(view.find('[role="dialog"]').exists()).toBe(false)
  } finally { view.unmount() }
})

it.each([[0, 0], [2, 0], [3, 20]])('regenerates the entire successful details group with %s uses and confirms %s credits', async (used, cost) => {
  const value = fixture(3, used)
  api.getQuickRun.mockResolvedValue(value)
  const pending: any = structuredClone(value)
  pending.version++; pending.state.pending_batch = 'next'
  pending.state.batches.push({ id: 'next', kind: 'image', submitted: false, items: [value.state.batches[2]!.items[0], { ...value.state.batches[2]!.items[1], task_id: null, free_regeneration: used < 3 }] })
  api.prepareQuickRun.mockResolvedValue(pending)
  const view = mount(QuickGenerationView, options); await flushPromises()
  try {
    const details = view.get('[data-task-id="new-details"]')
    const actions = details.findAll('button').filter(button => button.text() === '重新生成')
    expect(actions).toHaveLength(1)
    await actions[0]!.trigger('click'); await flushPromises()
    expect(api.prepareQuickRun).toHaveBeenCalledWith('images', 1, 'image', undefined, 1)
    expect(view.get('.quick-charge-total').text()).toContain(`${cost} 积分`)
    expect(api.submitQuickBatch).not.toHaveBeenCalled()
    expect(view.find('[data-task-id="main"]').exists()).toBe(true)
  } finally { view.unmount() }
})
