import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { reactive, ref } from 'vue'
import type { Schema } from '../../src/types/api'

const route = reactive({ params: { conversationId: 'results' }, path: '/workspace/results', query: { task: undefined as string | undefined } })
const api = vi.hoisted(() => ({ submitTaskIntent: vi.fn(), replace: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push: vi.fn(), replace: api.replace }) }))
vi.mock('../../src/api/tasks', () => ({ submitTaskIntent: api.submitTaskIntent }))
vi.mock('../../src/api/catalog', () => ({ listAgents: vi.fn(async () => []), quote: vi.fn() }))
vi.mock('../../src/api/conversations', () => ({ getProductVersion: vi.fn(), createProductVersion: vi.fn(), createConversation: vi.fn() }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(1), profile: ref({ user_id: 'result-owner' }), refreshAccount: vi.fn(async () => {}) }, onIdentityChange: () => () => {} }))
vi.mock('../../src/features/workspace/useTaskStream', () => {
  const stream = { latestTaskId: ref(''), tasks: ref<Schema<'TaskView'>[]>([]), details: ref<Record<string, Schema<'TaskDetail'>>>({}), fragments: ref({}), connectionState: ref('open'), reconnect: vi.fn(), refreshTask: vi.fn(async () => {}) }
  return { useTaskStream: () => stream }
})

import WorkspaceView from '../../src/features/workspace/WorkspaceView.vue'
import { useTaskStream } from '../../src/features/workspace/useTaskStream'
import { draftFor, taskDraftFor } from '../../src/features/workspace/drafts'
import { session } from '../../src/features/auth/session'
import ResultViewer from '../../src/components/ResultViewer.vue'

const stream = useTaskStream('')
const wrappers: VueWrapper[] = []
function resultWork(kind: Schema<'WorkView'>['kind'], fileId: string, text: string | null = null): Schema<'WorkView'> {
  return {
    work_id: 'long-image', task_id: 'task-image', conversation_id: 'results', message_id: 'message-image', kind, created_at: '2026-10-19T00:00:00Z',
    items: [{ file_id: fileId, file_version: 'version-1', item_key: 'result-1', actual_bytes: 4096, media_type: kind === 'copy' ? 'text/plain' : 'image/png', content_url: '/api/v1/files/' + fileId + '/content', text }],
  }
}
function detail(id: string, conversation = 'results') {
  return { conversation_id: conversation, task: { task_id: id, work_ids: [id + '-work-a', id + '-work-b'] }, input: { product_version: 'pv', product: { name: '商品' }, instruction: '仅详情展示的输入', material_versions: [], parameters: {} } } as unknown as Schema<'TaskDetail'>
}
function render() {
  const wrapper = mount(WorkspaceView, { global: { stubs: {
    AgentSelector: true, PromptEditor: true, QuotePanel: true, AppDrawer: true, AppDialog: true,
    TaskCard: { name: 'TaskCard', props: ['detail', 'fragment'], template: '<article :data-task-id="detail.task.task_id">{{ detail.task.work_ids.join(" ") }}</article>' },
  } } })
  wrappers.push(wrapper); return wrapper
}
beforeEach(() => {
  vi.clearAllMocks()
  route.params.conversationId = 'results'; route.path = '/workspace/results'; route.query.task = undefined
  stream.latestTaskId.value = 'newest'; stream.tasks.value = [detail('newest').task, detail('older').task]
  stream.details.value = { newest: detail('newest'), older: detail('older') }; stream.connectionState.value = 'open'
  const draft = draftFor('results'); draft.product = { product_id: 'product', version: 'pv', created_at: '', product: { name: '草稿商品' } }; draft.pending = null; draft.confirmed = null
  api.replace.mockImplementation(async location => { route.query.task = location.query.task })
})
afterEach(() => wrappers.splice(0).forEach(wrapper => wrapper.unmount()))

it('refreshes credits on settlement changes rather than every task progress update', async () => {
  stream.tasks.value = [{ ...detail('newest').task, state: 'RUNNING', state_version: 3, settlement_state: 'FROZEN' }]
  render(); await flushPromises()
  vi.mocked(session.refreshAccount).mockClear()
  stream.tasks.value = [{ ...stream.tasks.value[0], state: 'SAVING', state_version: 4 }]
  await flushPromises()
  expect(session.refreshAccount).not.toHaveBeenCalled()
  stream.tasks.value = [{ ...stream.tasks.value[0], state: 'SUCCEEDED', state_version: 5, settlement_state: 'CONSUMED' }]
  await flushPromises()
  expect(session.refreshAccount).toHaveBeenCalledTimes(1)
})

it('shows all works from the selected task without displaying other tasks or input messages', async () => {
  route.query.task = 'older'
  const wrapper = render(); await flushPromises()
  const results = wrapper.get('[aria-label="当前任务产物"]')
  expect(results.findAll('[data-task-id]')).toHaveLength(1)
  expect(results.get('[data-task-id]').attributes('data-task-id')).toBe('older')
  expect(results.text()).toContain('older-work-a older-work-b')
  expect(results.text()).not.toContain('newest-work')
  expect(results.text()).not.toContain('仅详情展示的输入')
})

it('defaults to the latest persisted task and retains its results while reconnecting', async () => {
  stream.tasks.value.reverse()
  const wrapper = render(); await flushPromises()
  expect(wrapper.get('[data-task-id]').attributes('data-task-id')).toBe('newest')
  stream.connectionState.value = 'recovering'; await flushPromises()
  expect(wrapper.get('[data-task-id]').attributes('data-task-id')).toBe('newest')
  expect(wrapper.find('.results-skeleton').exists()).toBe(false)
  expect(wrapper.text()).not.toContain('正在核对原任务')
})

it('does not substitute another task while the explicitly selected detail is still loading', async () => {
  route.query.task = 'pending-detail'; stream.latestTaskId.value = 'pending-detail'; stream.connectionState.value = 'recovering'
  const wrapper = render(); await flushPromises()
  expect(wrapper.find('[data-task-id]').exists()).toBe(false)
  expect(wrapper.find('.results-skeleton').exists()).toBe(true)
  stream.details.value = { ...stream.details.value, 'pending-detail': detail('pending-detail') }; await flushPromises()
  expect(wrapper.get('[data-task-id]').attributes('data-task-id')).toBe('pending-detail')
})

it('never displays a cached detail belonging to another conversation', async () => {
  route.query.task = 'foreign'; stream.details.value = { ...stream.details.value, foreign: detail('foreign', 'other-conversation') }
  const wrapper = render(); await flushPromises()
  expect(wrapper.find('[data-task-id]').exists()).toBe(false)
  expect(wrapper.text()).toContain('暂时无法展示该任务')
})

it('selects a newly admitted task when submitting from an older task', async () => {
  route.query.task = 'older'
  const draft = taskDraftFor('results', 'older')
  draft.confirmed = { conversation_id: 'results', agent_id: 'agent', input: detail('new').input, confirmed_quote: { credits: 8 } } as Schema<'SubmitTaskRequest'>
  api.submitTaskIntent.mockResolvedValue({ task: { task_id: 'new' } })
  const wrapper = render(); await flushPromises()
  await (wrapper.vm as unknown as { submit(): Promise<void> }).submit()
  expect(api.replace).toHaveBeenCalledWith({ path: '/workspace/results', query: { task: 'new' } })
  expect(stream.refreshTask).toHaveBeenCalledWith('new')
  expect(draft.pending).toBeNull()
})

it('selects an explicit retry result while ordinary media refresh keeps the current selection', async () => {
  route.query.task = 'older'
  const wrapper = render(); await flushPromises()
  wrapper.getComponent({ name: 'TaskCard' }).vm.$emit('mediaChanged')
  await flushPromises()
  expect(stream.reconnect).toHaveBeenCalledOnce()
  expect(route.query.task).toBe('older')
  wrapper.getComponent({ name: 'TaskCard' }).vm.$emit('mediaChanged', 'retry-task')
  await flushPromises()
  expect(route.query.task).toBe('retry-task')
  expect(stream.refreshTask).toHaveBeenCalledWith('retry-task')
})

it('opens an image preview from the displayed image and clears it when switching works', async () => {
  const imageWork = resultWork('image', 'long-file')
  const wrapper = mount(ResultViewer, { props: { work: imageWork }, global: { stubs: { AppDialog: { props: ['open'], template: '<div v-if="open" role="dialog"><slot /></div>' } } } })
  wrappers.push(wrapper)
  const image = wrapper.get('img')
  expect(image.attributes('src')).toBe('/api/v1/files/long-file/content')
  await image.trigger('click')
  expect(wrapper.find('[role="dialog"] img').exists()).toBe(true)
  await wrapper.setProps({ work: { ...resultWork('image', 'other-file'), work_id: 'another-work' } })
  expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  expect(wrapper.get('img').attributes('src')).toBe('/api/v1/files/other-file/content')
  await wrapper.get('img').trigger('keydown', { key: 'Enter' })
  expect(wrapper.find('[role="dialog"] img').exists()).toBe(true)
})

it('keeps the complete compact copy reachable from the keyboard', () => {
  const text = '完整文案\n' + '商品介绍'.repeat(500) + '\n最后一段'
  const wrapper = mount(ResultViewer, { props: { compact: true, work: resultWork('copy', 'copy-file', text) } })
  wrappers.push(wrapper)
  const copy = wrapper.get('.copy-result')
  expect(copy.text()).toBe(text)
  expect(copy.attributes('tabindex')).toBe('0')
  expect(copy.attributes('aria-label')).toContain('完整文案')
})
