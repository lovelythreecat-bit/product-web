import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import QuickGenerationView from '../../src/features/quick-generation/QuickGenerationView.vue'
import QuickCopyRequirements from '../../src/features/quick-generation/QuickCopyRequirements.vue'
import { copyTypeChoices, useQuickGeneration } from '../../src/features/quick-generation/useQuickGeneration'
import { session } from '../../src/features/auth/session'
import { getWork } from '../../src/api/works'
import { listAgents, quote } from '../../src/api/catalog'
import { getProductVersion } from '../../src/api/conversations'
import { ApiError } from '../../src/api/client'
const navigation = vi.hoisted(() => ({ update: vi.fn(), leave: vi.fn(), replace: vi.fn(), params: { runId: 'run-1' as string | undefined } }))
const api = vi.hoisted(() => ({ createQuickRun: vi.fn(), getQuickRun: vi.fn(), saveQuickRun: vi.fn(), listQuickRuns: vi.fn(), prepareQuickRun: vi.fn(), advanceQuickRun: vi.fn(), submitQuickBatch: vi.fn(), cancelQuickBatch: vi.fn() }))
vi.mock('../../src/api/quickGeneration', () => api)
vi.mock('vue-router', () => ({ useRoute: () => ({ params: navigation.params, query: {} }), useRouter: () => ({ push: vi.fn(), replace: navigation.replace }), onBeforeRouteLeave: navigation.leave, onBeforeRouteUpdate: navigation.update }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(1), profile: ref({ user_id: 'owner' }), refreshAccount: vi.fn().mockResolvedValue({}) } }))
vi.mock('../../src/api/catalog', () => ({ listAgents: vi.fn().mockResolvedValue([]), quote: vi.fn().mockResolvedValue({ credits: 20 }) }))
vi.mock('../../src/api/conversations', () => ({ getProductVersion: vi.fn().mockResolvedValue({ version: 'p1', product: { name: '杯子', product_type: 'home' } }) }))
vi.mock('../../src/api/works', () => ({ getWork: vi.fn().mockResolvedValue({ items: [{ text: '原始文案' }] }) }))
const draft = () => ({ product_version: 'p1', material_versions: [], copy_parameters: {}, copy_instruction: '', copy_text: '', image_platform: '', image_outputs: [], image_instruction: '', video_first_frame_file_id: '', video_instruction: '' })
const fixture = (step = 3) => ({ run_id: 'run-1', version: 1, conversation_id: 'c1', title: '杯子', step, state: { step, draft: draft(), confirmed_copy: '确认文案', confirmed_images: null, current: { copy: null, image: null, video: null }, pending_batch: null, batches: [] }, tasks: {} })
beforeEach(() => { vi.clearAllMocks(); navigation.params.runId = 'run-1'; api.getQuickRun.mockResolvedValue(fixture()); api.saveQuickRun.mockImplementation(async (_id, version, draft) => ({ ...fixture(), version: version + 1, state: { ...fixture().state, draft } })); api.listQuickRuns.mockResolvedValue([]); api.createQuickRun.mockResolvedValue({ run_id: 'first-run' }) })
const stubs = { RouterLink: { template: '<a><slot/></a>' }, TaskCard: true, QuickProductEditor: true, AppDialog: { template: '<div v-if="open"><slot/><slot name="actions"/></div>', props: ['open'] } }
it('requires explicit image selection and does not submit a task on entering the step', async () => {
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  expect(view.find('.quick-intro').exists()).toBe(false)
  expect(api.submitQuickBatch).not.toHaveBeenCalled()
  const generate = view.findAll('button').find(button => button.text().includes('确认费用并生成图片'))!
  await generate.trigger('click'); await flushPromises()
  expect(view.find('.quick-image-settings').exists()).toBe(true)
  await view.findAll('button').find(button => button.text() === '确认生成图片')!.trigger('click'); await flushPromises()
  expect(api.prepareQuickRun).not.toHaveBeenCalled()
  expect(view.text()).toContain('请选择目标平台')
  view.unmount()
})

it('keeps image selection in a dialog until costs are prepared', async () => {
  const value: any = fixture(2)
  value.state.draft.copy_text = '已确认文案'
  value.state.current.copy = 'copy'
  value.state.batches = [{ id: 'copy', kind: 'copy', submitted: true, items: [{ label: '文案', task_id: 'copy', request: { input: { parameters: {} } } }] }]
  value.tasks.copy = { task: { state: 'SUCCEEDED', settlement_state: 'CONSUMED', work_ids: [] } }
  api.getQuickRun.mockResolvedValueOnce(value)
  api.advanceQuickRun.mockResolvedValueOnce(fixture(3))
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    await view.findAll('button').find(button => button.text() === '确认文案，生成图片')!.trigger('click'); await flushPromises()
    expect(view.get('.quick-stepper [aria-current="step"]').text()).toContain('营销文案')
    expect(view.find('.quick-content .quick-image-settings').exists()).toBe(false)
    expect(view.find('.quick-image-settings').exists()).toBe(true)
    expect(api.prepareQuickRun).not.toHaveBeenCalled()
    expect(api.submitQuickBatch).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it('prepares only the chosen copy and displays the server free entitlement', async () => {
  const value = partialCopies()
  value.tasks['copy-2'].task = { ...value.tasks['copy-2'].task, state: 'SUCCEEDED', settlement_state: 'CONSUMED' }
  value.state.draft.copy_texts = { 宣传文案: '原文', 商品标题: '人工保留标题', 短视频脚本: '原脚本' }
  api.getQuickRun.mockResolvedValueOnce(value)
  const pending = structuredClone(value)
  pending.version++
  pending.state.pending_batch = 'single'
  pending.state.batches.push({ id: 'single', kind: 'copy', submitted: false, items: value.state.batches[0].items.map((item: any, index: number) => index === 1 ? { ...item, task_id: null, free_regeneration: true, free_regenerations_used: 0, request: { ...item.request, confirmed_quote: { credits: 10 } } } : item) })
  api.prepareQuickRun.mockResolvedValueOnce(pending)
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    const buttons = view.findAll('.quick-copy-paper')[1]!.findAll('button')
    const regenerate = buttons.find(button => button.text().includes('重新生成'))
    expect(regenerate).toBeDefined()
    await regenerate!.trigger('click'); await flushPromises()
    expect(api.prepareQuickRun).toHaveBeenCalledWith('run-1', 1, 'copy', undefined, 1)
    expect(view.get('.quick-charge-total').text()).toContain('0 积分')
    expect(view.get('[aria-label="商品标题"]').element).toHaveProperty('value', '人工保留标题')
    expect(api.submitQuickBatch).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it('recovers image admission from polling while the submission response is still pending', async () => {
  const initial: any = fixture(3)
  const item = { label: '商品主图', task_id: null, request: { input: { parameters: { output_type: 'main_image' } }, confirmed_quote: { credits: 20 } } }
  initial.state.pending_batch = 'images'
  initial.state.batches = [{ id: 'images', kind: 'image', submitted: false, items: [item] }]
  api.getQuickRun.mockResolvedValueOnce(initial)
  const { view, state } = controller(); await flushPromises()
  let resolveSubmit!: (value: unknown) => void
  api.submitQuickBatch.mockImplementationOnce(() => new Promise(resolve => { resolveSubmit = resolve }))
  const request = state.submit(); await flushPromises()
  const accepted = structuredClone(initial)
  accepted.version = 2; accepted.state.pending_batch = null; accepted.state.current.image = 'images'
  accepted.state.batches[0].submitted = true; accepted.state.batches[0].items[0].task_id = 'image-task'
  accepted.tasks['image-task'] = { task: { task_id: 'image-task', state: 'QUEUED', state_version: 1, settlement_state: 'FROZEN', work_ids: [] } }
  api.getQuickRun.mockResolvedValueOnce(accepted)
  try {
    await state.refresh()
    expect(state.busy.value).toBe(false)
    expect(state.chargeOpen.value).toBe(false)
    expect(state.stageStatus.value).toContain('后台排队')
    expect(state.current.value[0]?.task_id).toBe('image-task')
    expect(api.submitQuickBatch).toHaveBeenCalledTimes(1)
    // A delayed old receipt must not overwrite a newer progress response.
    const completed = structuredClone(accepted)
    completed.tasks['image-task'].task.state = 'SUCCEEDED'; completed.tasks['image-task'].task.settlement_state = 'CONSUMED'
    api.getQuickRun.mockResolvedValueOnce(completed)
    await state.refresh()
    resolveSubmit(accepted); await request
    expect(state.complete.value).toBe(true)
  } finally { view.unmount() }
})

it.each(['FEATURE_NOT_ENABLED', 'FORBIDDEN'])('makes a rejected image admission explicit for %s', async code => {
  const initial: any = fixture(3)
  initial.state.pending_batch = 'images'
  initial.state.batches = [{ id: 'images', kind: 'image', submitted: false, items: [{ label: '详情图', task_id: null }] }]
  api.getQuickRun.mockResolvedValueOnce(initial)
  api.submitQuickBatch.mockRejectedValueOnce(new ApiError('当前功能尚未启用。', 403, code, { error: { code, message: '当前功能尚未启用。' } } as any))
  const { view, state } = controller(); await flushPromises()
  try {
    await state.submit()
    expect(state.error.value).toContain('未受理')
    expect(state.error.value).toContain('未冻结积分')
    expect(state.chargeOpen.value).toBe(false)
    expect(state.uncertain.value).toBe(false)
    expect(state.busy.value).toBe(false)
    expect(state.current.value).toHaveLength(0)
  } finally { view.unmount() }
})

function controller() {
  let state!: ReturnType<typeof useQuickGeneration>
  const view = mount(defineComponent({ setup() { state = useQuickGeneration(); return () => h('div') } }))
  return { view, state }
}
it('opens the latest saved quick creation directly without an intermediate page or a new run', async () => {
  navigation.params.runId = undefined
  api.listQuickRuns.mockResolvedValueOnce([{ run_id: 'saved-run' }])
  const { view } = controller(); await flushPromises()
  try {
    expect(navigation.replace).toHaveBeenCalledWith('/workspace/quick/saved-run')
    expect(api.createQuickRun).not.toHaveBeenCalled()
    expect(api.submitQuickBatch).not.toHaveBeenCalled()
  } finally { view.unmount() }
})
it('creates the first quick draft directly and reuses its identity after a failed creation response', async () => {
  navigation.params.runId = undefined
  api.createQuickRun.mockRejectedValueOnce(new Error('创建暂时失败')).mockResolvedValueOnce({ run_id: 'first-run' })
  const { view, state } = controller(); await flushPromises()
  try {
    expect(state.error.value).toContain('创建暂时失败')
    await state.initialize(); await flushPromises()
    expect(api.createQuickRun.mock.calls[0][0]).toBe(api.createQuickRun.mock.calls[1][0])
    expect(navigation.replace).toHaveBeenCalledWith('/workspace/quick/first-run')
    expect(api.prepareQuickRun).not.toHaveBeenCalled()
  } finally { view.unmount() }
})
it('removes obsolete hidden copy fields before preparing a new charge while retaining saved snapshots', async () => {
  const value: any = fixture(1)
  value.state.draft.copy_instruction = '旧隐藏指令'
  value.state.draft.copy_parameters = { audience: false, tone: '自然' }
  api.getQuickRun.mockResolvedValueOnce(value)
  api.prepareQuickRun.mockResolvedValue(fixture(1))
  const { view, state } = controller(); await flushPromises()
  try {
    await state.prepare('copy')
    expect(api.saveQuickRun).toHaveBeenCalledWith('run-1', 1, expect.objectContaining({ copy_instruction: '', copy_parameters: { tone: '自然' } }))
    expect(value.state.draft.copy_instruction).toBe('旧隐藏指令')
    expect(value.state.draft.copy_parameters.audience).toBe(false)
    expect(api.prepareQuickRun).toHaveBeenCalled()
  } finally { view.unmount() }
})
it('allows opening a run or leaving the quick generation entry without trying to save a nonexistent draft', async () => {
  navigation.params.runId = undefined
  const { view, state } = controller(); await flushPromises()
  try {
    expect(await navigation.update.mock.calls.at(-1)![0]()).not.toBe(false)
    expect(await navigation.leave.mock.calls.at(-1)![0]()).not.toBe(false)
    expect(state.dirty.value).toBe(false)
    expect(state.error.value).toBe('')
    expect(api.saveQuickRun).not.toHaveBeenCalled()
  } finally { view.unmount() }
})
it('allows leaving a run that failed to load while keeping its read error visible', async () => {
  api.getQuickRun.mockRejectedValueOnce(new Error('进度暂时无法读取。'))
  const { view, state } = controller(); await flushPromises()
  try {
    expect(await navigation.leave.mock.calls.at(-1)![0]()).not.toBe(false)
    expect(state.error.value).toBe('进度暂时无法读取。')
    expect(state.dirty.value).toBe(false)
    expect(api.saveQuickRun).not.toHaveBeenCalled()
  } finally { view.unmount() }
})
it('keeps unsaved edits and blocks navigation if saving a loaded run fails', async () => {
  const { view, state } = controller(); await flushPromises()
  state.draft.value.copy_text = '尚未保存的人工文案'
  api.saveQuickRun.mockRejectedValueOnce(new Error('保存暂时失败。'))
  try {
    expect(await navigation.leave.mock.calls.at(-1)![0]()).toBe(false)
    expect(state.error.value).toBe('保存暂时失败。')
    expect(state.draft.value.copy_text).toBe('尚未保存的人工文案')
    expect(state.dirty.value).toBe(true)
  } finally { view.unmount() }
})
it('unlocks the recovered committed batch after an uncertain submission response', async () => {
  const value: any = fixture()
  value.state.pending_batch = 'b1'; value.state.batches = [{ id: 'b1', items: [] }]
  api.getQuickRun.mockResolvedValueOnce(value)
  const { view, state } = controller(); await flushPromises()
  expect(state.uncertain.value).toBe(true)
  api.getQuickRun.mockResolvedValue({ ...fixture(), version: 2 })
  await state.refresh()
  expect(state.uncertain.value).toBe(false)
  view.unmount()
})
it('clears a recovered progress read error without clearing a local validation error', async () => {
  const { view, state } = controller(); await flushPromises()
  try {
    api.getQuickRun.mockRejectedValueOnce(new Error('进度读取暂时失败'))
    await state.refresh()
    expect(state.error.value).toBe('进度读取暂时失败')
    api.getQuickRun.mockResolvedValueOnce(fixture())
    await state.refresh()
    expect(state.error.value).toBe('')
    state.error.value = '请选择目标平台。'
    await state.refresh()
    expect(state.error.value).toBe('请选择目标平台。')
  } finally { view.unmount() }
})
it('does not apply an old poll after a newer confirmed transition', async () => {
  const { view, state } = controller(); await flushPromises()
  let resolvePoll!: (value: unknown) => void
  api.getQuickRun.mockImplementationOnce(() => new Promise(resolve => { resolvePoll = resolve }))
  const poll = state.refresh()
  api.advanceQuickRun.mockResolvedValue({ ...fixture(4), version: 2 })
  await state.advance('confirm_images')
  resolvePoll(fixture(3)); await poll
  expect(state.step.value).toBe(4)
  expect(state.run.value?.version).toBe(2)
  view.unmount()
})
it('saves an edited draft before navigating to another quick generation route', async () => {
  const { view, state } = controller(); await flushPromises()
  state.draft.value.copy_text = '离开前保留的文案'
  await navigation.update.mock.calls.at(-1)![0]()
  expect(api.saveQuickRun).toHaveBeenCalledWith('run-1', 1, expect.objectContaining({ copy_text: '离开前保留的文案' }))
  view.unmount()
})
it('can cancel a recovered unsubmitted batch without charging or staying locked', async () => {
  const value: any = fixture()
  value.state.pending_batch = 'b1'; value.state.batches = [{ id: 'b1', items: [] }]
  api.getQuickRun.mockResolvedValueOnce(value)
  api.cancelQuickBatch.mockResolvedValue({ ...fixture(), version: 2 })
  const { view, state } = controller(); await flushPromises()
  expect(state.uncertain.value).toBe(true)
  await state.closeCharge(false)
  expect(api.cancelQuickBatch).toHaveBeenCalledWith('run-1', 'b1')
  expect(state.uncertain.value).toBe(false)
  expect(api.submitQuickBatch).not.toHaveBeenCalled()
  view.unmount()
})
it('refreshes the account when a background task settles', async () => {
  const running: any = fixture()
  running.tasks.t1 = { task: { task_id: 't1', state: 'RUNNING', state_version: 1, settlement_state: 'FROZEN' } }
  api.getQuickRun.mockResolvedValueOnce(running)
  const { view, state } = controller(); await flushPromises()
  const settled = JSON.parse(JSON.stringify(running))
  settled.tasks.t1.task = { ...settled.tasks.t1.task, state: 'SUCCEEDED', state_version: 2, settlement_state: 'CONSUMED' }
  api.getQuickRun.mockResolvedValue(settled)
  await state.refresh()
  expect(session.refreshAccount).toHaveBeenCalled()
  view.unmount()
})
it('preserves copy edits in the confirmed stage transition without rewriting original work', async () => {
  const value: any = fixture(2)
  value.state.current.copy = 'batch-copy'
  value.state.batches = [{ id: 'batch-copy', kind: 'copy', submitted: true, items: [{ label: '营销文案', task_id: 'copy-1' }] }]
  value.tasks['copy-1'] = { task: { task_id: 'copy-1', state: 'SUCCEEDED', settlement_state: 'CONSUMED', work_ids: [] } }
  api.getQuickRun.mockResolvedValue(value)
  api.advanceQuickRun.mockResolvedValue(fixture(3))
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  await view.get('[aria-label="营销文案"]').setValue('人工确认的新文案')
  await view.findAll('button').find(button => button.text().includes('确认文案，生成图片'))!.trigger('click'); await flushPromises()
  expect(api.saveQuickRun).toHaveBeenCalledWith('run-1', 1, expect.objectContaining({ copy_text: '人工确认的新文案' }))
  expect(api.advanceQuickRun).toHaveBeenCalledWith('run-1', 2, 'confirm_copy')
  expect(api.submitQuickBatch).not.toHaveBeenCalled()
  view.unmount()
})

it('moves to the submitted copy stage without waiting for account refresh or generation output', async () => {
  const initial: any = fixture(1)
  const item = { label: '营销文案', task_id: null, request: { confirmed_quote: { credits: 20 } } }
  initial.state.pending_batch = 'copy-batch'
  initial.state.batches = [{ id: 'copy-batch', kind: 'copy', submitted: false, items: [item] }]
  api.getQuickRun.mockResolvedValue(initial)
  const { view, state } = controller(); await flushPromises()
  const accepted: any = fixture(2)
  accepted.version = 2
  accepted.state.current.copy = 'copy-batch'
  accepted.state.batches = [{ id: 'copy-batch', kind: 'copy', submitted: true, items: [{ ...item, task_id: 'copy-task' }] }]
  accepted.tasks['copy-task'] = { task: { task_id: 'copy-task', state: 'QUEUED', state_version: 1, settlement_state: 'FROZEN', work_ids: [] } }
  api.submitQuickBatch.mockResolvedValue(accepted)
  vi.mocked(session.refreshAccount).mockImplementationOnce(() => new Promise(() => {}))
  try {
    void state.submit(); await flushPromises()
    expect(state.step.value).toBe(2)
    expect(state.chargeOpen.value).toBe(false)
    expect(state.busy.value).toBe(false)
    expect(state.stageStatus.value).toContain('后台')
    expect(state.complete.value).toBe(false)
    expect(getWork).not.toHaveBeenCalled()
    expect(await navigation.leave.mock.calls.at(-1)![0]()).not.toBe(false)
  } finally { view.unmount() }
})

it('keeps an executing stage explicit and prevents editing an unfinished copy result', async () => {
  const value: any = fixture(2)
  value.state.current.copy = 'copy-batch'
  value.state.batches = [{ id: 'copy-batch', kind: 'copy', submitted: true, items: [{ label: '营销文案', task_id: 'copy-task' }] }]
  value.tasks['copy-task'] = { task: { task_id: 'copy-task', state: 'RUNNING', state_version: 1, settlement_state: 'FROZEN', work_ids: [] } }
  api.getQuickRun.mockResolvedValue(value)
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    expect(view.get('[aria-label="营销文案"]').attributes('disabled')).toBeDefined()
    expect(view.get('.quick-stage-status').text()).toContain('后台')
    expect(view.get('.quick-stage-status').text()).toContain('生成')
    expect(view.findAll('button').find(button => button.text().includes('保存并退出'))!.attributes('disabled')).toBeUndefined()
  } finally { view.unmount() }
})

it('automatically recovers an accepted batch after losing its submission response without submitting again', async () => {
  vi.useFakeTimers()
  const initial: any = fixture(1)
  initial.state.pending_batch = 'batch'
  initial.state.batches = [{ id: 'batch', kind: 'copy', submitted: false, items: [{ label: '营销文案', task_id: null }] }]
  api.getQuickRun.mockResolvedValueOnce(initial)
  const { view, state } = controller(); await flushPromises()
  try {
    expect(state.uncertain.value).toBe(true)
    state.chargeOpen.value = true
    const accepted: any = fixture(2)
    accepted.version = 2
    api.getQuickRun.mockResolvedValue(accepted)
    await vi.advanceTimersByTimeAsync(3000); await flushPromises()
    expect(state.uncertain.value).toBe(false)
    expect(state.chargeOpen.value).toBe(false)
    expect(state.step.value).toBe(2)
    expect(api.submitQuickBatch).not.toHaveBeenCalled()
  } finally { view.unmount(); vi.useRealTimers() }
})

it('continues progress polling when the ancillary balance read has not returned', async () => {
  const initial: any = fixture(2)
  initial.tasks.t1 = { task: { task_id: 't1', state: 'QUEUED', state_version: 1, settlement_state: 'FROZEN', work_ids: [] } }
  api.getQuickRun.mockResolvedValueOnce(initial)
  const { view, state } = controller(); await flushPromises()
  const running = structuredClone(initial)
  running.tasks.t1.task.state = 'RUNNING'; running.tasks.t1.task.state_version++
  api.getQuickRun.mockResolvedValue(running)
  vi.mocked(session.refreshAccount).mockImplementationOnce(() => new Promise(() => {}))
  try {
    void state.refresh(); await flushPromises()
    void state.refresh(); await flushPromises()
    expect(api.getQuickRun).toHaveBeenCalledTimes(3)
    expect(session.refreshAccount).toHaveBeenCalledTimes(1)
  } finally { view.unmount() }
})

it('lets the server select copy materials by model capability instead of rejecting references reserved for media', async () => {
  const initial = fixture(1)
  initial.state.draft.material_versions = Array.from({ length: 4 }, (_, index) => ({ file_id: 'ref-' + index, version: 'v1' })) as any
  api.getQuickRun.mockResolvedValueOnce(initial)
  vi.mocked(listAgents).mockResolvedValueOnce([{ kind: 'copy', enabled: true, input_support: { min_materials: 0, max_materials: 0 } }] as any)
  api.prepareQuickRun.mockResolvedValueOnce({ ...initial, version: 2 })
  const { view, state } = controller(); await flushPromises()
  try {
    await state.prepare('copy')
    expect(state.error.value).toBe('')
    expect(state.chargeOpen.value).toBe(true)
    expect(api.prepareQuickRun).toHaveBeenCalledWith('run-1', 1, 'copy', undefined)
    expect(state.draft.value.material_versions).toHaveLength(4)
  } finally { view.unmount() }
})

it('only switches between unlocked stages without confirming stages or creating tasks', async () => {
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    const buttons = view.findAll('.quick-stepper button')
    expect(buttons).toHaveLength(4)
    expect(buttons[3]!.attributes('disabled')).toBeDefined()
    await buttons[3]!.trigger('click'); await flushPromises()
    expect(view.get('.quick-stepper [aria-current="step"]').text()).toContain('图片生成')
    for (const index of [0, 1, 2]) {
      await buttons[index]!.trigger('click'); await flushPromises()
      expect(view.get('.quick-stepper [aria-current="step"]').text()).toContain(['商品确认', '营销文案', '图片生成', '视频生成'][index])
    }
    expect(api.advanceQuickRun).not.toHaveBeenCalled()
    expect(api.prepareQuickRun).not.toHaveBeenCalled()
    expect(api.submitQuickBatch).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it('preserves edits and the current view when saving before a step switch fails', async () => {
  const { view, state } = controller(); await flushPromises()
  try {
    state.draft.value.image_instruction = '保留商品实物'
    api.saveQuickRun.mockRejectedValueOnce(new Error('保存暂时失败。'))
    await state.goToStep(2)
    expect(state.step.value).toBe(3)
    expect(state.draft.value.image_instruction).toBe('保留商品实物')
    expect(state.error.value).toBe('保存暂时失败。')
  } finally { view.unmount() }
})

it('allows viewing other stages while a task runs and keeps editing locked', async () => {
  const value: any = fixture(2)
  value.tasks.copy = { task: { task_id: 'copy', state: 'RUNNING', settlement_state: 'FROZEN', state_version: 1 } }
  api.getQuickRun.mockResolvedValueOnce(value)
  const { view, state } = controller(); await flushPromises()
  try {
    expect(state.locked.value).toBe(true)
    await state.goToStep(1)
    expect(state.step.value).toBe(1)
    expect(state.progressStep.value).toBe(2)
    expect(state.locked.value).toBe(true)
    expect(api.saveQuickRun).not.toHaveBeenCalled()
    expect(api.advanceQuickRun).not.toHaveBeenCalled()
    expect(api.submitQuickBatch).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it('clears the previous stage fee immediately when switching steps', async () => {
  vi.useFakeTimers()
  const value: any = fixture(3)
  value.state.draft.image_platform = 'taobao'; value.state.draft.image_outputs = ['main_image']
  api.getQuickRun.mockResolvedValueOnce(value)
  vi.mocked(listAgents).mockResolvedValueOnce([{ agent_id: 'image', version: 'v1', kind: 'image', enabled: true }] as any)
  const { view, state } = controller(); await flushPromises()
  try {
    await vi.advanceTimersByTimeAsync(300); await flushPromises()
    expect(state.estimated.value).toBe(20)
    await state.goToStep(2)
    expect(state.estimated.value).toBeNull()
  } finally { view.unmount(); vi.useRealTimers() }
})

it('keeps all media references in the draft for later media stages', async () => {
  const value: any = fixture(1)
  value.state.draft.material_versions = Array.from({ length: 5 }, (_, i) => ({ file_id: 'reference-' + i, version: 'v1' }))
  api.getQuickRun.mockResolvedValueOnce(value)
  vi.mocked(listAgents).mockResolvedValueOnce([{ agent_id: 'copy', version: 'v1', kind: 'copy', enabled: true, input_support: { max_materials: 4 } }] as any)
  const { view, state } = controller(); await flushPromises()
  try {
    expect(state.draft.value.material_versions).toHaveLength(5)
  } finally { view.unmount() }
})

it('adds each selected image quote once, including the three-image detail quote', async () => {
  vi.useFakeTimers()
  const value: any = fixture(3)
  value.state.draft.image_platform = 'taobao'; value.state.draft.image_outputs = ['main_image', 'detail_page', 'long_image']
  value.state.draft.copy_texts = { 详情介绍: '已确认的详情内容', 营销策略: '不应传给图片的策略全文' }
  value.state.confirmed_copy = '【详情介绍】\n已确认的详情内容\n\n【营销策略】\n不应传给图片的策略全文'
  value.state.current.copy = 'confirmed-copies'
  value.state.batches = [{ id: 'confirmed-copies', kind: 'copy', items: ['详情介绍', '营销策略'].map(copy_type => ({ label: copy_type, request: { input: { parameters: { copy_type } } } })) }]
  api.getQuickRun.mockResolvedValueOnce(value)
  vi.mocked(listAgents).mockResolvedValueOnce([{ agent_id: 'image', kind: 'image', enabled: true }] as any)
  vi.mocked(quote).mockImplementation(async request => ({ credits: request.input.parameters.output_type === 'detail_page' ? 60 : 20 }) as any)
  const { view, state } = controller(); await flushPromises()
  try {
    await vi.advanceTimersByTimeAsync(300); await flushPromises()
    expect(state.estimated.value).toBe(100)
    for (const [request] of vi.mocked(quote).mock.calls) {
      expect(request.input.instruction).toBe('已确认的详情内容')
      expect(request.input.instruction).not.toContain('不应传给图片的策略全文')
    }
    vi.mocked(quote).mockClear()
    state.run.value!.state.batches![0]!.items[0]!.request.input.parameters.copy_type = '营销策略'
    state.draft.value.image_instruction = '新的图片要求'
    await vi.advanceTimersByTimeAsync(300); await flushPromises()
    expect(quote).toHaveBeenCalled()
    for (const [request] of vi.mocked(quote).mock.calls) {
      expect(request.input.instruction).not.toContain('已确认的详情内容')
      expect(request.input.instruction).toBe('')
    }
  } finally { view.unmount(); vi.useRealTimers(); vi.mocked(quote).mockResolvedValue({ credits: 20 } as any) }
})

it('uses a confirmed generated image as the single video material without changing product references', async () => {
  const value: any = fixture(4)
  value.state.draft.material_versions = [{ file_id: 'reference', version: 'v1' }]
  value.state.draft.video_first_frame_file_id = 'generated'
  value.state.confirmed_images = value.state.current.image = 'images'
  value.state.batches = [{ id: 'images', kind: 'image', submitted: true, items: [{ label: '商品主图 · 1 张', task_id: 'image-task' }] }]
  value.tasks['image-task'] = { task: { task_id: 'image-task', state: 'SUCCEEDED', settlement_state: 'CONSUMED', work_ids: ['image-work'] } }
  api.getQuickRun.mockResolvedValue(value)
  vi.mocked(listAgents).mockResolvedValueOnce([{ agent_id: 'video', version: 'v1', kind: 'video', enabled: true, input_support: { min_materials: 1, max_materials: 1 } }] as any)
  vi.mocked(getProductVersion).mockResolvedValueOnce({ version: 'p1', product: { name: '杯子', product_type: 'home', category: '家居' } } as any)
  vi.mocked(getWork).mockResolvedValueOnce({ kind: 'image', items: [{ file_id: 'generated', file_version: 'gv1', media_type: 'image/png' }] } as any)
  const { view, state } = controller(); await flushPromises()
  try {
    expect(state.frameCandidates.value).toContainEqual(expect.objectContaining({ file_id: 'generated', version: 'gv1' }))
    expect(state.videoMaterials.value).toEqual([{ file_id: 'generated', version: 'gv1' }])
    expect(state.draft.value.material_versions).toEqual([{ file_id: 'reference', version: 'v1' }])
    await state.prepare('video')
    expect(api.prepareQuickRun).toHaveBeenCalledWith('run-1', 1, 'video', undefined)
  } finally { view.unmount() }
})

it('opens copy requirements before preparing a charge and leaves the product page uncluttered', async () => {
  api.getQuickRun.mockResolvedValueOnce(fixture(1))
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    expect(view.find('.quick-content .text-choices').exists()).toBe(false)
    await view.findAll('button').find(button => button.text() === '确认商品，生成文案')!.trigger('click'); await flushPromises()
    expect(view.text()).not.toContain('额外写作要求')
    expect(view.text()).not.toContain('最大字符数')
    expect(view.findAll('.el-select__selected-item').map(item => item.text()).join(' ')).toContain('营销策略')
    expect(view.get('input[aria-label="目标平台"]').element).toHaveProperty('value', '淘宝')
    expect(view.get('input[aria-label="语气"]').element).toHaveProperty('value', '自然')
    expect(view.find('[aria-label="文案类型"]').exists()).toBe(true)
    expect(api.prepareQuickRun).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it('defaults to every copy type when an old single-type parameter exists without an explicit selection', async () => {
  const value: any = fixture(1)
  value.state.draft.copy_types = []
  value.state.draft.copy_parameters = { copy_type: '宣传文案' }
  api.getQuickRun.mockResolvedValueOnce(value)
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    await view.findAll('button').find(button => button.text() === '确认商品，生成文案')!.trigger('click'); await flushPromises()
    const dialog = view.findComponent(QuickCopyRequirements)
    expect(dialog.emitted('change')?.at(-1)?.[0]).toEqual(copyTypeChoices)
    expect(api.prepareQuickRun).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it('confirms copy options and the displayed credits in one dialog before submitting once', async () => {
  vi.useFakeTimers()
  const initial: any = fixture(1)
  api.getQuickRun.mockResolvedValueOnce(initial)
  vi.mocked(listAgents).mockResolvedValueOnce([{ agent_id: 'copy', kind: 'copy', enabled: true, input_support: { product_required_fields: [] } }] as any)
  api.saveQuickRun.mockImplementationOnce(async (_id, version, draft) => ({ ...initial, version: version + 1, state: { ...initial.state, draft } }))
  const pending: any = fixture(1)
  pending.version = 3; pending.state.pending_batch = 'copies'
  pending.state.batches = [{ id: 'copies', kind: 'copy', submitted: false, items: Array.from({ length: 7 }, (_, index) => ({ label: '文案' + index, task_id: null, request: { input: { parameters: {} }, confirmed_quote: { credits: 20 } } })) }]
  api.prepareQuickRun.mockResolvedValueOnce(pending)
  api.submitQuickBatch.mockImplementationOnce(() => new Promise(() => {}))
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    await view.findAll('button').find(button => button.text() === '确认商品，生成文案')!.trigger('click'); await flushPromises()
    await vi.advanceTimersByTimeAsync(300); await flushPromises()
    expect(view.get('.quick-charge-total').text()).toContain('140 积分')
    expect(view.findAll('.quick-copy-requirements')).toHaveLength(1)
    await view.findAll('button').find(button => button.text() === '确认生成文案')!.trigger('click'); await flushPromises()
    expect(api.submitQuickBatch).toHaveBeenCalledExactlyOnceWith('run-1', 'copies')
    expect(view.findAll('.quick-charge-total')).toHaveLength(1)
  } finally { view.unmount(); vi.useRealTimers() }
})

it('discards unconfirmed copy settings when the merged dialog is cancelled', async () => {
  api.getQuickRun.mockResolvedValueOnce(fixture(1))
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    await view.findAll('button').find(button => button.text() === '确认商品，生成文案')!.trigger('click')
    await view.get('input[aria-label="目标平台"]').setValue('京东')
    view.findComponent(QuickCopyRequirements).vm.$emit('update:open', false); await flushPromises()
    await view.findAll('button').find(button => button.text() === '保存并退出')!.trigger('click'); await flushPromises()
    expect(api.saveQuickRun).not.toHaveBeenCalled()
    expect(api.prepareQuickRun).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it('keeps image selection and exact credits in one dialog and submits only that confirmed batch', async () => {
  const initial: any = fixture(3)
  initial.state.draft.image_platform = 'taobao'; initial.state.draft.image_outputs = ['detail_page']
  api.getQuickRun.mockResolvedValueOnce(initial)
  vi.mocked(getProductVersion).mockResolvedValueOnce({ version: 'p1', product: { name: '杯子', category: '家居', product_type: 'home' } } as any)
  const pending = structuredClone(initial)
  pending.version = 2; pending.state.pending_batch = 'detail-images'
  pending.state.batches = [{ id: 'detail-images', kind: 'image', submitted: false, items: [{ label: '详情图 · 3 张', task_id: null, request: { input: { parameters: { output_type: 'detail_page' } }, confirmed_quote: { credits: 60 } } }] }]
  api.prepareQuickRun.mockResolvedValueOnce(pending)
  api.submitQuickBatch.mockImplementationOnce(() => new Promise(() => {}))
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    await view.findAll('button').find(button => button.text() === '确认费用并生成图片')!.trigger('click')
    await view.findAll('button').find(button => button.text() === '确认生成图片')!.trigger('click'); await flushPromises()
    expect(view.findAll('.quick-charge-total')).toHaveLength(1)
    expect(view.get('.quick-charge-total').text()).toContain('60 积分')
    expect(view.find('.quick-image-settings').exists()).toBe(true)
    expect(api.submitQuickBatch).not.toHaveBeenCalled()
    await view.findAll('button').find(button => button.text() === '确认生成图片')!.trigger('click'); await flushPromises()
    expect(api.submitQuickBatch).toHaveBeenCalledExactlyOnceWith('run-1', 'detail-images')
  } finally { view.unmount() }
})

it.each([[1, 'copy'], [2, 'image'], [3, 'video']] as const)('uses only navigation in step %s after downstream tasks exist, even while they run', async (step, kind) => {
  const value: any = fixture(step + 1)
  value.state.current[kind] = 'generated'
  value.state.batches = [{ id: 'generated', kind, submitted: true, items: [{ label: kind, task_id: 'task', request: { input: { parameters: { output_type: kind === 'image' ? 'main_image' : undefined } } } }] }]
  value.tasks.task = { task: { task_id: 'task', state: 'RUNNING', settlement_state: 'FROZEN', work_ids: [] } }
  api.getQuickRun.mockResolvedValueOnce(value)
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    await view.findAll('.quick-stepper button')[step - 1]!.trigger('click'); await flushPromises()
    const footer = view.get('.quick-footer')
    expect(footer.findAll('button').map(button => button.text())).toEqual(step === 1 ? ['下一步'] : ['上一步', '下一步'])
    expect(footer.text()).not.toContain('积分')
    expect(footer.find('.quick-footer-hint').exists()).toBe(false)
    await footer.findAll('button').at(-1)!.trigger('click'); await flushPromises()
    expect(view.get('.quick-stepper [aria-current="step"]').text()).toContain(['商品确认', '营销文案', '图片生成', '视频生成'][step])
    expect(api.prepareQuickRun).not.toHaveBeenCalled()
    expect(api.advanceQuickRun).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it('loads every selected copy type and saves independent edits', async () => {
  const value: any = fixture(2)
  value.state.draft.copy_types = ['宣传文案', '商品标题']; value.state.draft.copy_texts = {}
  value.state.current.copy = 'copies'
  value.state.batches = [{ id: 'copies', kind: 'copy', submitted: true, items: ['宣传文案', '商品标题'].map((label, index) => ({ label, task_id: 'copy-' + index, request: { input: { parameters: { copy_type: label } } } })) }]
  for (const index of [0, 1]) value.tasks['copy-' + index] = { task: { task_id: 'copy-' + index, state: 'SUCCEEDED', settlement_state: 'CONSUMED', work_ids: ['work-' + index] } }
  vi.mocked(getWork).mockImplementation(async id => ({ items: [{ text: id === 'work-0' ? '宣传原稿' : '标题原稿' }] }) as any)
  api.getQuickRun.mockResolvedValue(value)
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    expect((view.get('[aria-label="宣传文案"]').element as HTMLTextAreaElement).value).toBe('宣传原稿')
    expect((view.get('[aria-label="商品标题"]').element as HTMLTextAreaElement).value).toBe('标题原稿')
    await view.get('[aria-label="商品标题"]').setValue('人工标题')
    await view.findAll('button').find(button => button.text() === '确认文案，生成图片')!.trigger('click'); await flushPromises()
    expect(api.saveQuickRun).toHaveBeenCalledWith('run-1', 1, expect.objectContaining({ copy_texts: { 宣传文案: '宣传原稿', 商品标题: '人工标题' } }))
  } finally { view.unmount() }
})

it('keeps completed history read only across all four stages and returns to the summary without mutations', async () => {
  const value: any = fixture(5)
  value.state.draft.copy_text = '历史确认文案'
  value.state.confirmed_copy = '历史确认文案'
  api.getQuickRun.mockResolvedValueOnce(value)
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    for (let index = 0; index < 4; index++) {
      await view.findAll('.quick-stepper button')[index]!.trigger('click'); await flushPromises()
      const footer = view.get('.quick-footer')
      expect(footer.findAll('button').map(button => button.text())).toEqual(index === 0 ? ['下一步'] : index === 3 ? ['上一步', '查看汇总'] : ['上一步', '下一步'])
      expect(footer.find('.quick-footer-hint').exists()).toBe(false)
      expect(view.find('.quick-content .action-row').exists()).toBe(false)
      if (index === 1) expect(view.get('textarea[aria-label="营销文案"]').attributes('readonly')).toBeDefined()
      await footer.findAll('button').at(-1)!.trigger('click'); await flushPromises()
    }
    expect(view.find('.quick-completed-section').exists()).toBe(true)
    expect(api.saveQuickRun).not.toHaveBeenCalled()
    expect(api.prepareQuickRun).not.toHaveBeenCalled()
    expect(api.advanceQuickRun).not.toHaveBeenCalled()
    expect(api.submitQuickBatch).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it('guards completed history commands and ignores edits when navigating', async () => {
  api.getQuickRun.mockResolvedValueOnce(fixture(5))
  const { view, state } = controller(); await flushPromises()
  try {
    state.draft.value.copy_text = '不应保存的修改'
    expect(state.dirty.value).toBe(false)
    await state.prepare('copy')
    await state.advance('confirm_copy')
    await state.submit()
    await state.goToStep(1)
    expect(state.step.value).toBe(1)
    expect(api.saveQuickRun).not.toHaveBeenCalled()
    expect(api.prepareQuickRun).not.toHaveBeenCalled()
    expect(api.advanceQuickRun).not.toHaveBeenCalled()
    expect(api.submitQuickBatch).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it.each([1, 2, 3])('guards direct navigation beyond progress step %s', async progress => {
  api.getQuickRun.mockResolvedValueOnce(fixture(progress))
  const { view, state } = controller(); await flushPromises()
  try {
    await state.goToStep(progress + 1)
    expect(state.step.value).toBe(progress)
    expect(api.saveQuickRun).not.toHaveBeenCalled()
    expect(api.advanceQuickRun).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it('rechecks unlocked stages after saving upstream edits invalidates downstream progress', async () => {
  api.getQuickRun.mockResolvedValueOnce(fixture(4))
  const { view, state } = controller(); await flushPromises()
  try {
    await state.goToStep(2)
    state.draft.value.copy_text = '新确认文案'
    api.saveQuickRun.mockResolvedValueOnce({ ...fixture(2), version: 2 })
    await state.goToStep(4)
    expect(state.progressStep.value).toBe(2)
    expect(state.step.value).toBe(2)
  } finally { view.unmount() }
})

function partialCopies() {
  const value: any = fixture(2)
  value.state.draft.copy_types = ['宣传文案', '商品标题', '短视频脚本']
  value.state.draft.copy_texts = { 商品标题: '人工保留标题' }
  value.state.current.copy = 'copies'
  value.state.batches = [{ id: 'copies', kind: 'copy', submitted: true, items: ['宣传文案', '商品标题', '短视频脚本'].map((label, index) => ({ label, task_id: 'copy-' + index, request: { input: { parameters: { copy_type: label } } } })) }]
  for (const index of [0, 1, 2]) value.tasks['copy-' + index] = { task: { task_id: 'copy-' + index, state: index === 2 ? 'FAILED' : 'SUCCEEDED', settlement_state: index === 2 ? 'FROZEN' : 'CONSUMED', work_ids: index === 2 ? [] : ['work-' + index] } }
  return value
}

it('restores successful copies independently and fills a retried copy without overwriting saved edits', async () => {
  const value = partialCopies()
  api.getQuickRun.mockResolvedValueOnce(value)
  vi.mocked(getWork).mockImplementation(async id => ({ items: [{ text: id === 'work-0' ? '已成功宣传文案' : '重试成功脚本' }] }) as any)
  const { view, state } = controller(); await flushPromises()
  try {
    expect(state.draft.value.copy_texts).toEqual({ 商品标题: '人工保留标题', 宣传文案: '已成功宣传文案' })
    expect(state.complete.value).toBe(false)
    const recovered = structuredClone(value)
    recovered.tasks['copy-2'].task = { ...recovered.tasks['copy-2'].task, state: 'SUCCEEDED', settlement_state: 'CONSUMED', work_ids: ['work-2'] }
    api.getQuickRun.mockResolvedValueOnce(recovered)
    await state.refresh()
    expect(state.draft.value.copy_texts).toEqual({ 商品标题: '人工保留标题', 宣传文案: '已成功宣传文案', 短视频脚本: '重试成功脚本' })
    expect(getWork).not.toHaveBeenCalledWith('work-1')
    expect(state.dirty.value).toBe(true)
    api.advanceQuickRun.mockResolvedValueOnce(fixture(3))
    await state.advance('confirm_copy')
    expect(api.saveQuickRun).toHaveBeenCalledWith('run-1', 1, expect.objectContaining({ copy_texts: { 商品标题: '人工保留标题', 宣传文案: '已成功宣传文案', 短视频脚本: '重试成功脚本' } }))
  } finally { view.unmount() }
})

it('allows leaving a partially successful stage without saving a task-locked draft', async () => {
  api.getQuickRun.mockResolvedValueOnce(partialCopies())
  const { view, state } = controller(); await flushPromises()
  try {
    expect(state.draft.value.copy_texts['宣传文案']).toBeTruthy()
    expect(state.locked.value).toBe(true)
    expect(state.dirty.value).toBe(false)
    await state.goToStep(1)
    expect(state.step.value).toBe(1)
    expect(await navigation.leave.mock.calls.at(-1)![0]()).not.toBe(false)
    expect(api.saveQuickRun).not.toHaveBeenCalled()
  } finally { view.unmount() }
})

it('keeps original tasks collapsed behind one toggle even when some copies failed', async () => {
  api.getQuickRun.mockResolvedValueOnce(partialCopies())
  const view = mount(QuickGenerationView, { global: { stubs } }); await flushPromises()
  try {
    const toggle = view.findAll('button').find(button => button.text() === '查看原始任务')!
    expect(toggle).toBeDefined()
    expect(toggle.attributes('aria-expanded')).toBe('false')
    expect(view.findAll('task-card-stub')).toHaveLength(0)
    await toggle.trigger('click')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(view.findAll('task-card-stub')).toHaveLength(3)
    await toggle.trigger('click')
    expect(view.findAll('task-card-stub')).toHaveLength(0)
  } finally { view.unmount() }
})
