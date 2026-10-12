import { afterEach, expect, it, vi } from 'vitest'
import { effectScope, ref } from 'vue'

const modules = import.meta.glob('../../src/features/workspace/useTaskStream.ts')
const task = (version: number, state = 'RUNNING') => ({ task_id: 'task-a', state, state_version: version, settlement_state: 'FROZEN', investigation_reason: null, work_ids: [], quote: { credits: 8, agent_version: 'a1', spec_id: 's1', spec_version: 's1', price_version: 'p1', input_digest: 'fixed', policy_versions: {} } })
class Events {
  static all: Events[] = []
  listeners = new Map<string, (e: MessageEvent) => void>()
  onerror: (() => void) | null = null
  onopen: (() => void) | null = null
  closed = false
  constructor(public url: string) { Events.all.push(this) }
  addEventListener(name: string, listener: (e: MessageEvent) => void) { this.listeners.set(name, listener) }
  close() { this.closed = true }
  emit(name: string, data: unknown, id = '') { this.listeners.get(name)?.(new MessageEvent(name, { data: JSON.stringify(data), lastEventId: id })) }
}
const scopes: ReturnType<typeof effectScope>[] = []
afterEach(() => { scopes.forEach(s => s.stop()); scopes.length = 0; Events.all = []; vi.unstubAllGlobals(); vi.resetModules() })
async function setup() {
  expect(Object.keys(modules), '缺少真实任务流消费者，无法恢复原任务').toHaveLength(1)
  vi.stubGlobal('EventSource', Events)
  let version = 3
  const gets: string[] = []
  vi.stubGlobal('fetch', async (url: string) => {
    gets.push(url)
    const value = url.startsWith('/api/v1/conversations/') ? { conversation: { conversation_id: 'conversation-a', title: 'A' }, tasks: { items: [task(version)], next_cursor: null }, messages: { items: [], next_cursor: null } }
      : url.startsWith('/api/v1/tasks/task-a') ? { task: task(version), conversation_id: 'conversation-a', agent_id: 'a', input: { product: {}, product_version: 'v', instruction: '', parameters: {}, material_versions: [] }, policy_versions: {} }
      : { items: url.startsWith('/api/v1/tasks?') ? [task(version)] : [], next_cursor: null }
    return new Response(JSON.stringify(value))
  })
  const api = await Object.values(modules)[0]() as typeof import('../../src/features/workspace/useTaskStream')
  const scope = effectScope(); scopes.push(scope)
  const conversation = ref('conversation-a')
  const stream = scope.run(() => api.useTaskStream(conversation))!
  await vi.waitFor(() => expect(Events.all.length).toBe(1))
  return { stream, gets, conversation, setVersion: (value: number) => { version = value } }
}
it('unwraps durable payload, keeps opaque reset cursor, GETs originals before reopening and rejects older versions', async () => {
  const { stream, gets, setVersion } = await setup()
  expect(stream.tasks.value[0].state_version).toBe(3)
  setVersion(2)
  Events.all[0].emit('task.updated', { event_seq: 1, payload: { task_id: 'task-a', state: 'RUNNING', state_version: 2 }, created_at: '' }, 'user:opaque:1')
  await new Promise(r => setTimeout(r, 10))
  expect(stream.tasks.value[0].state_version).toBe(3)
  Events.all[0].emit('reset', { reason: 'expired' }, 'user:opaque:reset')
  await vi.waitFor(() => expect(Events.all.length).toBe(2))
  expect(Events.all[0].closed).toBe(true)
  expect(gets.some(x => x.startsWith('/api/v1/works?'))).toBe(true)
  expect(Events.all[1].url).toBe('/api/v1/events?after=user%3Aopaque%3Areset')
  expect(stream.tasks.value[0].state_version).toBe(3)
})
it('clears old conversation before GET and closes the owned EventSource on disposal', async () => {
  const { stream, conversation } = await setup()
  conversation.value = ''
  await vi.waitFor(() => expect(stream.tasks.value).toEqual([]))
  expect(Events.all[0].closed).toBe(true)
  scopes[0].stop()
  expect(stream.connectionState.value).toBe('closed')
})
it('a protected 401 after opaque EventSource error closes the connection and clears user data', async () => {
  const { stream } = await setup()
  vi.stubGlobal('fetch', async () => new Response(JSON.stringify({ error: { code: 'UNAUTHENTICATED', message: '请重新登录。' } }), { status: 401 }))
  Events.all[0].onerror?.()
  await vi.waitFor(() => expect(stream.connectionState.value).toBe('closed'))
  expect(stream.tasks.value).toEqual([])
  expect(Events.all[0].closed).toBe(true)
  expect(Events.all).toHaveLength(1)
})
