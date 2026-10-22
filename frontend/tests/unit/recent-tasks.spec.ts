import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import ConversationList from '../../src/features/workspace/ConversationList.vue'
import { session } from '../../src/features/auth/session'

const api = vi.hoisted(() => ({ listTasks: vi.fn(), getTask: vi.fn(), deleteTask: vi.fn(), createConversation: vi.fn(), listConversations: vi.fn(), listQuickRuns: vi.fn(), createQuickRun: vi.fn() }))
vi.mock('../../src/api/quickGeneration', () => ({ listQuickRuns: api.listQuickRuns, createQuickRun: api.createQuickRun }))
vi.mock('../../src/api/tasks', () => ({ listTasks: api.listTasks, getTask: api.getTask, deleteTask: api.deleteTask }))
vi.mock('../../src/api/conversations', () => ({ createConversation: api.createConversation, listConversations: api.listConversations }))
vi.mock('../../src/features/auth/session', () => ({ session: { epoch: ref(1), account: ref(null) } }))
const wrappers: VueWrapper[] = []
const first = { task_id: 'task-new', display_number: 'T002', state: 'RUNNING', state_version: 2, created_at: '2026-10-17T02:30:00Z' }
const second = { task_id: 'task-old', display_number: 'T001', state: 'SUCCEEDED', state_version: 4, created_at: '2026-10-16T02:30:00Z' }
beforeEach(() => {
  vi.resetAllMocks()
  api.listQuickRuns.mockResolvedValue([{ run_id: 'quick-one', title: '快速商品', step: 1 }])
  api.listTasks.mockResolvedValue({ items: [first, second], next_cursor: null })
  api.getTask.mockImplementation(async id => ({ conversation_id: 'shared', task: id === 'task-new' ? first : second, input: { product: { name: '陶瓷马克杯' } } }))
  api.listConversations.mockResolvedValue({ items: [{conversation_id:'shared', title:'原会话', created_at:'2026-10-17'}], next_cursor: null })
})
afterEach(() => wrappers.splice(0).forEach(wrapper => wrapper.unmount()))
async function setup(path = '/workspace/shared?task=task-old') {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/workspace/quick/:runId?', component: { template: '<div />' } }, { path: '/:pathMatch(.*)*', component: { template: '<div />' } }] })
  await router.push(path); await router.isReady()
  const wrapper = mount(ConversationList, { global: { plugins: [router] } }); wrappers.push(wrapper)
  await flushPromises()
  return { wrapper, router }
}
it('lists individual tasks from the same conversation and selects their precise task links', async () => {
  const { wrapper, router } = await setup()
  const links = wrapper.findAll('.task-history-item')
  expect(links).toHaveLength(2)
  expect(links[0].attributes('href')).toBe('/workspace/shared?task=task-new')
  expect(links[1].attributes('aria-current')).toBe('page')
  expect(links[0].attributes('aria-current')).toBeUndefined()
  expect(links[0].text()).toContain('陶瓷马克杯')
  expect(links[0].text()).toContain('生成中')
  expect(links[0].find('time').attributes('datetime')).toBe('2026-10-17T02:30:00Z')
  await links[0].trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query.task).toBe('task-new')
  expect(wrapper.findAll('.task-history-item[aria-current="page"]')).toHaveLength(1)
})
it('keeps task pagination and starts an independent draft without a prior task query', async () => {
  api.listTasks.mockResolvedValueOnce({ items: [first], next_cursor: 'older' }).mockResolvedValue({ items: [second], next_cursor: null })
  api.createConversation.mockResolvedValue({ conversation_id: 'new-draft' })
  const { wrapper, router } = await setup()
  await wrapper.findAll('button').find(button => button.text() === '更多任务')!.trigger('click'); await flushPromises()
  expect(wrapper.findAll('.task-history-item')).toHaveLength(2)
  expect(api.listTasks).toHaveBeenCalledWith(undefined, 'older', undefined, 'ordinary')
  await wrapper.findAll('button').find(button => button.text() === '新建任务')!.trigger('click'); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/workspace/new-draft')
  expect(router.currentRoute.value.query.task).toBeUndefined()
})

it('switches workspace modes and only displays the matching history on desktop and mobile', async () => {
  const { wrapper, router } = await setup('/workspace/quick/quick-one')
  expect(wrapper.findAll('.task-history-item').map(item => item.text())).toEqual([expect.stringContaining('快速商品')])
  expect(wrapper.get('select[data-select-id="task-choice"]').text()).not.toContain('陶瓷马克杯')
  expect(api.listTasks).not.toHaveBeenCalled()
  await wrapper.get('a[href="/workspace/ordinary"]').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/workspace/ordinary')
  expect(wrapper.findAll('.task-history-item')).toHaveLength(2)
  expect(wrapper.get('select[data-select-id="task-choice"]').text()).not.toContain('快速商品')
  expect(api.listTasks).toHaveBeenCalledWith(undefined, undefined, undefined, 'ordinary')
  await wrapper.get('a[href="/workspace/quick"]').trigger('click'); await flushPromises()
  expect(wrapper.findAll('.task-history-item')).toHaveLength(1)
  expect(wrapper.find('.task-delete').exists()).toBe(false)
})

it('creates a quick draft directly and keeps the same creation identity when retrying', async () => {
  api.createQuickRun.mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ run_id: 'new-quick' })
  const { wrapper, router } = await setup('/workspace/quick/quick-one')
  const create = () => wrapper.findAll('button').find(button => button.text() === '新建快速生成')!
  await create().trigger('click'); await flushPromises()
  expect(wrapper.get('.creation-error').text()).toContain('创建失败')
  await create().trigger('click'); await flushPromises()
  expect(api.createQuickRun.mock.calls[0][0]).toBe(api.createQuickRun.mock.calls[1][0])
  expect(router.currentRoute.value.path).toBe('/workspace/quick/new-quick')
  expect(api.createConversation).not.toHaveBeenCalled()
})

it('does not expose a quick run identifier while its history entry has not loaded', async () => {
  const { wrapper } = await setup('/workspace/quick/new-not-in-history')
  expect(wrapper.get('.el-select__placeholder').text()).toBe('选择最近任务')
})
it('ignores a pending history response after the navigation is disposed', async () => {
  let resolve!: (value: unknown) => void
  api.listTasks.mockImplementation(() => new Promise(ok => { resolve = ok }))
  const { wrapper } = await setup()
  wrapper.unmount()
  resolve({ items: [first], next_cursor: null }); await flushPromises()
  expect(api.getTask).not.toHaveBeenCalled()
})

it('shows creation progress and keeps a creation failure beside the button across history refreshes', async () => {
  let reject!: (reason: Error) => void
  api.createConversation.mockImplementation(() => new Promise((_, fail) => { reject = fail }))
  const { wrapper, router } = await setup()
  const button = wrapper.findAll('button').find(button => button.text() === '新建任务')!
  await button.trigger('click')
  expect(button.text()).toContain('创建中')
  expect(button.attributes('disabled')).toBeDefined()
  reject(new Error('HTTP 500')); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/workspace/shared?task=task-old')
  expect(button.text()).toBe('新建任务')
  expect(button.attributes('disabled')).toBeUndefined()
  const error = wrapper.get('.creation-error')
  expect(error.attributes('role')).toBe('alert')
  expect(error.text()).toContain('新任务创建失败')
  expect(wrapper.element.querySelector('.desktop-history')!.compareDocumentPosition(error.element) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy()
  ;(session.account as unknown as { value: unknown }).value = { available: 23 }
  await flushPromises()
  expect(wrapper.get('.creation-error').text()).toContain('新任务创建失败')
  api.createConversation.mockResolvedValue({ conversation_id: 'retry-draft' })
  await button.trigger('click'); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/workspace/retry-draft')
  expect(wrapper.find('.creation-error').exists()).toBe(false)
})

it('updates task state silently while retaining loaded older tasks and the exhausted cursor', async () => {
  api.listTasks.mockResolvedValueOnce({ items: [first], next_cursor: 'older' })
    .mockResolvedValueOnce({ items: [second], next_cursor: null })
    .mockResolvedValue({ items: [{ ...first, state: 'SUCCEEDED', state_version: 3 }], next_cursor: 'older' })
  const { wrapper } = await setup()
  await wrapper.findAll('button').find(button => button.text() === '更多任务')!.trigger('click'); await flushPromises()
  ;(session.account as unknown as { value: unknown }).value = { available: 20 }
  await flushPromises()
  expect(wrapper.findAll('.task-history-item')).toHaveLength(2)
  expect(wrapper.findAll('.task-history-item')[0].text()).toContain('生成成功')
  expect(wrapper.findAll('button').some(button => button.text() === '更多任务')).toBe(false)
  expect(wrapper.find('[role="status"]').exists()).toBe(false)
})
it('uses the mobile task selector to open the task rather than only its conversation', async () => {
  const { wrapper, router } = await setup()
  await wrapper.get('select[data-select-id="task-choice"]').setValue('task-new'); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/workspace/shared?task=task-new')
})
it('clears cached tasks at the identity boundary and discards the previous identity response', async () => {
  const { wrapper } = await setup()
  let resolveOld!: (value: unknown) => void
  api.listTasks.mockImplementationOnce(() => new Promise(ok => { resolveOld = ok }))
  ;(session.account as unknown as { value: unknown }).value = { available: 21 }
  await flushPromises()
  api.listTasks.mockResolvedValue({ items: [], next_cursor: null })
  ;(session.epoch as unknown as { value: number }).value++
  await flushPromises()
  expect(wrapper.findAll('.task-history-item')).toHaveLength(0)
  resolveOld({ items: [first], next_cursor: null }); await flushPromises()
  expect(wrapper.findAll('.task-history-item')).toHaveLength(0)
})
it('updates pagination availability during refresh before any older page was loaded', async () => {
  const { wrapper } = await setup()
  expect(wrapper.findAll('button').some(button => button.text() === '更多任务')).toBe(false)
  api.listTasks.mockResolvedValue({ items: [first, second], next_cursor: 'new-older-page' })
  ;(session.account as unknown as { value: unknown }).value = { available: 22 }
  await flushPromises()
  expect(wrapper.findAll('button').some(button => button.text() === '更多任务')).toBe(true)
})
it('recovers a failed task detail from the exhausted older page when retrying history', async () => {
  api.listTasks.mockResolvedValueOnce({ items: [first], next_cursor: 'older' })
    .mockResolvedValueOnce({ items: [second], next_cursor: null })
    .mockResolvedValue({ items: [first], next_cursor: 'older' })
  let olderAttempts = 0
  api.getTask.mockImplementation(async id => {
    if (id === 'task-old' && olderAttempts++ === 0) throw new Error('offline')
    return { conversation_id: 'shared', task: id === 'task-new' ? first : second, input: { product: { name: '陶瓷马克杯' } } }
  })
  const { wrapper } = await setup()
  await wrapper.findAll('button').find(button => button.text() === '更多任务')!.trigger('click'); await flushPromises()
  expect(wrapper.findAll('.task-history-item')).toHaveLength(1)
  expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  expect(wrapper.findAll('button').some(button => button.text() === '更多任务')).toBe(false)
  await wrapper.findAll('button').find(button => button.text() === '重试')!.trigger('click'); await flushPromises()
  expect(wrapper.findAll('.task-history-item')).toHaveLength(2)
  expect(wrapper.findAll('.task-history-item')[1].attributes('href')).toBe('/workspace/shared?task=task-old')
  expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  expect(wrapper.findAll('button').some(button => button.text() === '更多任务')).toBe(false)
})

it('confirms deletion, removes only that task, and does not revive it on a stale refresh', async () => {
  const { wrapper, router } = await setup()
  await wrapper.get('button[aria-label="删除任务：陶瓷马克杯"]').trigger('click')
  expect(api.deleteTask).not.toHaveBeenCalled()
  expect(wrapper.get('[role="dialog"]').text()).toContain('继续执行')
  await wrapper.findAll('button').find(button => button.text() === '确认删除')!.trigger('click')
  await flushPromises()
  expect(api.deleteTask).toHaveBeenCalledExactlyOnceWith('task-new')
  expect(wrapper.findAll('.task-history-item')).toHaveLength(1)
  expect(router.currentRoute.value.query.task).toBe('task-old')
  ;(session.account as unknown as { value: unknown }).value = { available: 24 }
  await flushPromises()
  expect(wrapper.findAll('.task-history-item')).toHaveLength(1)
  expect(wrapper.get('.task-history-item').attributes('href')).toContain('task-old')
})

it('retains a task after a failed deletion and switches away only after successful deletion', async () => {
  const { wrapper, router } = await setup('/workspace/shared?task=task-new')
  api.deleteTask.mockRejectedValueOnce(new Error('offline')).mockResolvedValue(undefined)
  await wrapper.get('button[aria-label="删除任务：陶瓷马克杯"]').trigger('click')
  const confirm = () => wrapper.findAll('button').find(button => button.text() === '确认删除')!
  await confirm().trigger('click'); await flushPromises()
  expect(wrapper.findAll('.task-history-item')).toHaveLength(2)
  expect(wrapper.get('[role="dialog"] [role="alert"]').text()).toContain('删除失败')
  expect(router.currentRoute.value.query.task).toBe('task-new')
  await confirm().trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query.task).toBe('task-old')
  expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
})

it('offers deletion of the selected task on mobile and cancellation leaves history intact', async () => {
  const { wrapper } = await setup()
  await wrapper.get('.mobile-task-delete').trigger('click')
  await wrapper.findAll('button').find(button => button.text() === '取消')!.trigger('click')
  await flushPromises()
  expect(api.deleteTask).not.toHaveBeenCalled()
  expect(wrapper.findAll('.task-history-item')).toHaveLength(2)
})
