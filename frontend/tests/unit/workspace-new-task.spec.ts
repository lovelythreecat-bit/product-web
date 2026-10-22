import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { ref, toValue, watch } from 'vue'

const api = vi.hoisted(() => ({ quote: vi.fn(), submitTaskIntent: vi.fn(), getProductVersion: vi.fn() }))
vi.mock('../../src/api/catalog', () => ({ listAgents: vi.fn(async () => [{ agent_id: 'copy', version: 'copy-v1', name: '文案', kind: 'copy', enabled: true, protocol_version: 'text-agent-v1', input_support: { product_required_fields: ['name'], min_materials: 0, max_materials: 3, instruction_required: false } }]), quote: api.quote }))
vi.mock('../../src/api/tasks', () => ({ submitTaskIntent: api.submitTaskIntent }))
vi.mock('../../src/api/conversations', () => ({ getProductVersion: api.getProductVersion, createProductVersion: vi.fn(), createConversation: vi.fn() }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(1), profile: ref({ user_id: 'new-task-owner' }), refreshAccount: vi.fn(async () => {}) }, onIdentityChange: () => () => {} }))
vi.mock('../../src/features/workspace/useTaskStream', () => ({ useTaskStream: (conversation: any) => {
  const tasks = ref([]), details = ref({}), latestTaskId = ref('')
  watch(() => toValue(conversation), () => { tasks.value = []; details.value = {}; latestTaskId.value = '' }, { immediate: true, flush: 'sync' })
  return { tasks, details, latestTaskId, fragments: ref({}), connectionState: ref('open'), reconnect: vi.fn(), refreshTask: vi.fn(async () => {}) }
} }))

import WorkspaceView from '../../src/features/workspace/WorkspaceView.vue'
import { draftFor } from '../../src/features/workspace/drafts'

const wrappers: VueWrapper[] = []
beforeEach(() => { vi.clearAllMocks(); api.quote.mockResolvedValue({ credits: 8 }); api.submitTaskIntent.mockResolvedValue({ task: { task_id: 'admitted-copy' } }) })
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()) })

async function openNewTask() {
  const previous = 'previous-' + crypto.randomUUID(), next = 'next-' + crypto.randomUUID()
  const oldDraft = draftFor(previous)
  oldDraft.agentId = 'copy'; oldDraft.agents.copy = { specId: '', instruction: '保留原指令', parameters: {} }
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/workspace/:conversationId', component: WorkspaceView }] })
  await router.push('/workspace/' + previous); await router.isReady()
  const wrapper = mount(RouterView, { global: { plugins: [router], stubs: { TaskCard: true } } })
  wrappers.push(wrapper); await flushPromises()
  await router.push('/workspace/' + next); await flushPromises()
  return { wrapper, router, draft: draftFor(next), oldDraft, next }
}

it('initializes all copy fields when the router opens a new task using the same creation type', async () => {
  const { wrapper, draft, oldDraft } = await openNewTask()
  expect(wrapper.find('[aria-label="文本创作要求"]').exists()).toBe(true)
  expect(wrapper.find('#creation-instruction').exists()).toBe(false)
  expect(draft.agents.copy).toEqual({ specId: '', instruction: '', parameters: {} })
  expect(oldDraft.agents.copy.instruction).toBe('保留原指令')
})

it('creates the new copy task through fee confirmation without switching creation type', async () => {
  const { wrapper, router, draft, next } = await openNewTask()
  draft.product = { product_id: 'p', version: 'pv', created_at: '', product: { name: '新任务商品' } }
  await flushPromises()
  await wrapper.get('.generate-button').trigger('click'); await flushPromises()
  expect(wrapper.find('[role="dialog"]').exists(), wrapper.text()).toBe(true)
  await wrapper.findAll('button').find(button => button.text() === '确认并冻结积分')!.trigger('click'); await flushPromises()
  expect(api.submitTaskIntent).toHaveBeenCalledOnce()
  expect(JSON.parse(api.submitTaskIntent.mock.calls[0][0].body)).toMatchObject({ conversation_id: next, agent_id: 'copy', input: { product: { name: '新任务商品' } } })
  expect(router.currentRoute.value.query.task).toBe('admitted-copy')
  expect(draft.pending).toBeNull()
})
