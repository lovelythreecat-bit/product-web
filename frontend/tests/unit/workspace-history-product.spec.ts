import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { reactive, ref } from 'vue'
import type { Schema } from '../../src/types/api'

const api = vi.hoisted(() => ({ getProductVersion: vi.fn() }))
const identity = vi.hoisted(() => ({ epoch: { value: 1 }, profile: { value: { user_id: 'history-product-owner' } }, refreshAccount: vi.fn(async () => {}) }))
const route = reactive({ params: { conversationId: '' } })
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push: vi.fn() }) }))
vi.mock('../../src/api/conversations', () => ({ getProductVersion: api.getProductVersion, createProductVersion: vi.fn(), createConversation: vi.fn() }))
vi.mock('../../src/api/catalog', () => ({ listAgents: vi.fn(async () => []), quote: vi.fn() }))
vi.mock('../../src/features/auth/session', () => ({ session: identity, onIdentityChange: () => () => {} }))
vi.mock('../../src/features/workspace/useTaskStream', () => {
  const stream = { latestTaskId: ref(''), tasks: ref([]), details: ref({}), fragments: ref({}), connectionState: ref('open'), reconnect: vi.fn(), refreshTask: vi.fn() }
  return { useTaskStream: () => stream }
})
import WorkspaceView from '../../src/features/workspace/WorkspaceView.vue'
import { useTaskStream } from '../../src/features/workspace/useTaskStream'
import { draftFor, taskDraftFor } from '../../src/features/workspace/drafts'

const stream = useTaskStream('')
const wrappers: VueWrapper[] = []
const overlay = { props: ['open'], emits: ['update:open'], template: '<aside v-if="open"><slot/><button @click="$emit(\'update:open\', false)">取消</button><slot name="actions"/></aside>' }
function render() {
  const wrapper = mount(WorkspaceView, { global: { stubs: { AppDrawer: overlay, AppDialog: true, TaskCard: true, PromptEditor: true, AgentSelector: true } } })
  wrappers.push(wrapper); return wrapper
}
function detail(conversation: string, task = 'newest-task', version = 'product-v1') {
  return { conversation_id: conversation, agent_id: 'original-agent', task: { task_id: task, state_version: 1, work_ids: [] }, input: { product_version: version, product: {name:'原商品',category:'家居',brand:'原品牌',notes:'完整补充说明'}, instruction:'原指令', parameters:{}, material_versions:[] } } as unknown as Schema<'TaskDetail'>
}
function product(name = '历史商品') { return { product_id:'product', version:'product-v1', created_at:'2026-10-16T00:00:00Z', product:{name, category:'家居', brand:'原品牌', notes:'完整补充说明'} } as Schema<'ProductVersionView'> }
function history(conversation: string) {
  route.params.conversationId = conversation
  const latest = detail(conversation, conversation + '-newest-task')
  const older = detail(conversation, conversation + '-old-task', 'old-product')
  stream.latestTaskId.value = latest.task.task_id
  stream.tasks.value = [older.task, latest.task]
  stream.details.value = { [latest.task.task_id]: latest, [older.task.task_id]: older }
}
beforeEach(() => {
  vi.resetAllMocks(); identity.epoch.value = 1
  route.params.conversationId = 'history-' + crypto.randomUUID()
  stream.latestTaskId.value = ''; stream.tasks.value = []; stream.details.value = {}
  api.getProductVersion.mockResolvedValue(product())
})
afterEach(() => wrappers.splice(0).forEach(wrapper => wrapper.unmount()))

it('restores the newest immutable task input without overwriting an independent conversation draft', async () => {
  history(route.params.conversationId)
  const draft = draftFor(route.params.conversationId)
  draft.agentId = 'manually-selected'; draft.agents[draft.agentId] = {specId:'',instruction:'未提交的新要求',parameters:{tone:'温和'}}
  draft.materials = [{file_id:'local-reference',version:'v2'}]
  const wrapper = render(); await flushPromises()
  expect(api.getProductVersion).toHaveBeenCalledExactlyOnceWith('product-v1')
  expect(draft.product).toBeNull()
  expect(taskDraftFor(route.params.conversationId,stream.latestTaskId.value).product?.product.name).toBe('原商品')
  expect(wrapper.get('.product-details').text()).toContain('完整补充说明')
  expect(draft.agentId).toBe('manually-selected')
  expect(draft.agents[draft.agentId].instruction).toBe('未提交的新要求')
  expect(draft.materials).toEqual([{file_id:'local-reference',version:'v2'}])
})

it.each(['product', 'pending', 'confirmed', 'sourceWorkId'] as const)('does not replace a draft with existing %s', async field => {
  history(route.params.conversationId)
  const draft = draftFor(route.params.conversationId)
  if (field === 'product') draft.product = product('正在编辑的商品')
  else if (field === 'sourceWorkId') draft.sourceWorkId = 'existing-source'
  else if (field === 'pending') draft.pending = {key:'same-paid-intent',body:'{}'}
  else draft.confirmed = {} as Schema<'SubmitTaskRequest'>
  render(); await flushPromises()
  if (field === 'pending') expect(api.getProductVersion).not.toHaveBeenCalled()
  else expect(api.getProductVersion).toHaveBeenCalledExactlyOnceWith('product-v1')
  if (field === 'product') expect(draft.product?.product.name).toBe('正在编辑的商品')
})

it('blocks input editing and regeneration while the immutable source is being read', async () => {
  history(route.params.conversationId)
  let resolve!: (value: Schema<'ProductVersionView'>) => void
  api.getProductVersion.mockImplementationOnce(() => new Promise(ok => {resolve=ok})).mockImplementation(() => new Promise(() => {}))
  const wrapper = render(); await flushPromises()
  expect(wrapper.findAll('button').some(b => b.text()==='填写资料')).toBe(false)
  expect(wrapper.get('.generate-button').element.matches(':disabled')).toBe(true)
  resolve(product('迟到的旧响应')); await flushPromises()
  expect(taskDraftFor(route.params.conversationId,stream.latestTaskId.value).product?.product.name).toBe('原商品')
})

it('rejects the original response after A to B to A navigation', async () => {
  const first = route.params.conversationId
  history(first)
  let resolve!: (value: Schema<'ProductVersionView'>) => void
  api.getProductVersion.mockImplementationOnce(() => new Promise(ok => {resolve=ok})).mockImplementation(() => new Promise(() => {}))
  render(); await flushPromises()
  history(first + '-b'); await flushPromises()
  history(first); await flushPromises()
  resolve(product('第一次进入 A 的响应')); await flushPromises()
  expect(taskDraftFor(first,first+'-newest-task').product).toBeNull()
  expect(taskDraftFor(first+'-b',first+'-b-newest-task').product).toBeNull()
})

it('ignores a product response from a revoked identity', async () => {
  history(route.params.conversationId)
  let resolve!: (value: Schema<'ProductVersionView'>) => void
  api.getProductVersion.mockImplementation(() => new Promise(ok => {resolve=ok}))
  render(); await flushPromises(); identity.epoch.value++
  resolve(product()); await flushPromises()
  expect(taskDraftFor(route.params.conversationId,stream.latestTaskId.value).product).toBeNull()
})

it('does not overwrite an independent product draft while its task lookup is pending', async () => {
  history(route.params.conversationId)
  let resolve!: (value: Schema<'ProductVersionView'>) => void
  api.getProductVersion.mockImplementation(() => new Promise(ok => {resolve=ok}))
  render(); await flushPromises()
  draftFor(route.params.conversationId).product = product('刚保存的新商品')
  resolve(product('历史旧商品')); await flushPromises()
  expect(draftFor(route.params.conversationId).product?.product.name).toBe('刚保存的新商品')
})

it('does not fill a draft after leaving the workspace', async () => {
  history(route.params.conversationId)
  let resolve!: (value: Schema<'ProductVersionView'>) => void
  api.getProductVersion.mockImplementation(() => new Promise(ok => {resolve=ok}))
  const wrapper=render(); await flushPromises(); wrapper.unmount()
  resolve(product()); await flushPromises()
  expect(taskDraftFor(route.params.conversationId,stream.latestTaskId.value).product).toBeNull()
})

it('leaves empty conversations alone and offers a read retry after history lookup fails', async () => {
  const wrapper=render(); await flushPromises()
  expect(api.getProductVersion).not.toHaveBeenCalled()
  api.getProductVersion.mockRejectedValueOnce(new Error('temporary read failure')).mockResolvedValue(product())
  history(route.params.conversationId); await flushPromises()
  expect(wrapper.text()).toContain('历史商品资料暂时无法读取')
  await wrapper.findAll('button').find(b=>b.text()==='重试回填资料')!.trigger('click'); await flushPromises()
  expect(taskDraftFor(route.params.conversationId,stream.latestTaskId.value).product?.product.name).toBe('原商品')
})
