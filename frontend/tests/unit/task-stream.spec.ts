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
afterEach(() => { scopes.forEach(s => s.stop()); scopes.length = 0; Events.all = []; vi.unstubAllGlobals(); vi.useRealTimers(); vi.resetModules() })
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
  expect(gets.some(x => x.startsWith('/api/v1/tasks?'))).toBe(true)
  expect(Events.all[1].url).toBe('/api/v1/events?after=user%3Aopaque%3Areset')
  expect(stream.tasks.value[0].state_version).toBe(3)
})
it('clears old conversation before GET and closes the owned EventSource on disposal', async () => {
  const { stream, conversation } = await setup()
  expect(stream.latestTaskId.value).toBe('task-a')
  conversation.value = ''
  await vi.waitFor(() => expect(stream.tasks.value).toEqual([]))
  expect(Events.all[0].closed).toBe(true)
  expect(stream.latestTaskId.value).toBe('')
  scopes[0].stop()
  expect(stream.connectionState.value).toBe('closed')
})
it('keeps persisted results visible while a reconnect reconciles in the background', async () => {
  const { stream } = await setup()
  const previous = stream.details.value['task-a']
  let resume!: (response: Response) => void
  vi.stubGlobal('fetch', async (url: string) => {
    if (url.startsWith('/api/v1/conversations/')) return new Promise<Response>(resolve => { resume = resolve })
    return new Response(JSON.stringify(url.startsWith('/api/v1/tasks/task-a') ? previous : { items: url.startsWith('/api/v1/tasks?') ? [task(3)] : [], next_cursor: null }))
  })
  const reconnecting = stream.reconnect()
  expect(stream.connectionState.value).toBe('recovering')
  expect(stream.tasks.value.map(task => task.task_id)).toEqual(['task-a'])
  expect(stream.details.value['task-a']).toBe(previous)
  resume(new Response('{}'))
  await reconnecting
  expect(Events.all).toHaveLength(2)
  expect(stream.tasks.value.map(task => task.task_id)).toEqual(['task-a'])
})
it('publishes the newest listed task even when older task details arrive first', async () => {
  const { stream } = await setup()
  let resolveLatest!: (response: Response) => void
  vi.stubGlobal('fetch', async (url: string) => {
    if (url.startsWith('/api/v1/tasks/task-new')) return new Promise<Response>(resolve => { resolveLatest=resolve })
    const value = url.startsWith('/api/v1/conversations/') ? {}
      : url.startsWith('/api/v1/tasks?') ? {items:[{...task(1),task_id:'task-new'},task(3)],next_cursor:null}
      : url.startsWith('/api/v1/tasks/task-a') ? {task:task(3),conversation_id:'conversation-a',input:{product_version:'old-product'}}
      : {items:[],next_cursor:null}
    return new Response(JSON.stringify(value))
  })
  const pending = stream.reconnect()
  await vi.waitFor(() => expect(stream.latestTaskId.value).toBe('task-new'))
  expect(stream.tasks.value[0].task_id).toBe('task-a')
  resolveLatest(new Response(JSON.stringify({task:{...task(1),task_id:'task-new'},conversation_id:'conversation-a',input:{product_version:'new-product'}})))
  await pending
  expect(stream.details.value[stream.latestTaskId.value].input.product_version).toBe('new-product')
  expect(stream.tasks.value.map(t => t.task_id)).toEqual(['task-new', 'task-a'])
})
it('places newly received tasks first by creation time and never moves an old task after a status update', async () => {
  const { stream } = await setup()
  let version = 1
  vi.stubGlobal('fetch', async (url: string) => new Response(JSON.stringify({
    task: {...task(version), task_id:url.includes('task-new')?'task-new':'task-a', created_at:url.includes('task-new')?'2026-10-16T02:00:00Z':'2026-10-16T01:00:00Z'},
    conversation_id:'conversation-a',input:{product_version:'v'},
  })))
  await stream.refreshTask('task-new')
  expect(stream.tasks.value.map(t => t.task_id)).toEqual(['task-new', 'task-a'])
  version = 4
  await stream.refreshTask('task-a')
  expect(stream.tasks.value.map(t => t.task_id)).toEqual(['task-new', 'task-a'])
  expect(stream.latestTaskId.value).toBe('task-new')
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

it('updates media phases with the same task version through SSE and stays idle without polling', async () => {
  const { stream, gets } = await setup()
  vi.useFakeTimers()
  let mediaRevision = 1
  vi.stubGlobal('fetch', async (url: string) => {
    gets.push(url)
    return new Response(JSON.stringify({ task: task(3), conversation_id: 'conversation-a',
      media: { kind: 'video', revision: mediaRevision, status: 'awaiting_confirmation' } }))
  })
  Events.all[0].emit('task.updated', { payload: { task_id: 'task-a', state_version: 3, media_revision: 1 } }, 'user:1')
  await vi.advanceTimersByTimeAsync(0)
  expect((stream.details.value['task-a'].media as { status: string }).status).toBe('awaiting_confirmation')
  const count = gets.length, previous = stream.details.value['task-a']
  await vi.advanceTimersByTimeAsync(30000)
  expect(gets).toHaveLength(count)
  Events.all[0].emit('task.updated', { payload: { task_id: 'task-a', state_version: 3, media_revision: 1 } }, 'user:2')
  await vi.advanceTimersByTimeAsync(0)
  expect(gets).toHaveLength(count)
  expect(stream.details.value['task-a']).toBe(previous)
  mediaRevision = 2
  Events.all[0].emit('task.updated', { payload: { task_id: 'task-a', state_version: 3, media_revision: 2 } }, 'user:3')
  await vi.advanceTimersByTimeAsync(0)
  expect((stream.details.value['task-a'].media as { revision: number }).revision).toBe(2)
})

it('ignores events from other conversations without fetching their private detail', async () => {
  const { gets } = await setup()
  const count = gets.length
  Events.all[0].emit('task.updated', { payload: { task_id: 'elsewhere', state_version: 1, conversation_id: 'conversation-b' } }, 'user:1')
  await new Promise(r => setTimeout(r, 10))
  expect(gets).toHaveLength(count)
})

it('resolves legacy event scope once instead of fetching another conversation for every replayed state', async () => {
  const { gets } = await setup()
  const count = gets.length
  vi.stubGlobal('fetch', async (url: string) => {
    gets.push(url)
    return new Response(JSON.stringify({ task: { ...task(8), task_id: 'legacy-other' }, conversation_id: 'conversation-b' }))
  })
  for (const state_version of [1, 2, 3]) Events.all[0].emit('task.updated', {
    payload: { task_id: 'legacy-other', state_version },
  }, 'user:' + state_version)
  await vi.waitFor(() => expect(gets.length).toBeGreaterThan(count))
  await new Promise(r => setTimeout(r, 10))
  expect(gets).toHaveLength(count + 1)
})

it('reconnects an interrupted stream with backoff without reloading history', async () => {
  const { gets } = await setup()
  vi.useFakeTimers()
  const count = gets.filter(url => url.startsWith('/api/v1/tasks?') || url.startsWith('/api/v1/conversations/')).length
  Events.all[0].onerror?.()
  await vi.advanceTimersByTimeAsync(2500)
  expect(Events.all).toHaveLength(2)
  expect(gets.filter(url => url.startsWith('/api/v1/tasks?') || url.startsWith('/api/v1/conversations/'))).toHaveLength(count)
  Events.all[1].onerror?.()
  await vi.advanceTimersByTimeAsync(2500)
  expect(Events.all).toHaveLength(2)
  await vi.advanceTimersByTimeAsync(2500)
  expect(Events.all).toHaveLength(3)
})

it('does not refetch unchanged terminal task details during recovery', async () => {
  const { stream, gets } = await setup()
  vi.stubGlobal('fetch', async (url: string) => {
    gets.push(url)
    return new Response(JSON.stringify(url.startsWith('/api/v1/tasks/task-a')
      ? { task: task(4, 'SUCCEEDED'), conversation_id: 'conversation-a' }
      : { items: url.startsWith('/api/v1/tasks?') ? [task(4, 'SUCCEEDED')] : [], next_cursor: null }))
  })
  await stream.refreshTask('task-a')
  const previous = stream.details.value['task-a']
  const count = gets.filter(url => url.startsWith('/api/v1/tasks/task-a')).length
  await stream.reconnect()
  expect(gets.filter(url => url.startsWith('/api/v1/tasks/task-a'))).toHaveLength(count)
  expect(stream.details.value['task-a']).toBe(previous)
})

it('coalesces in-flight reads and catches up when a media event arrives after their snapshot', async () => {
  const { stream } = await setup()
  let finish!: (response: Response) => void
  let reads = 0
  vi.stubGlobal('fetch', async () => {
    reads++
    if (reads === 1) return new Promise<Response>(resolve => { finish = resolve })
    return new Response(JSON.stringify({ task: task(3), conversation_id: 'conversation-a',
      media: { kind: 'video', revision: 3, status: 'awaiting_confirmation' } }))
  })
  const first = stream.refreshTask('task-a')
  const duplicate = stream.refreshTask('task-a')
  expect(reads).toBe(1)
  Events.all[0].emit('task.updated', { payload: { task_id: 'task-a', state_version: 3, media_revision: 3 } }, 'user:3')
  await Promise.resolve()
  finish(new Response(JSON.stringify({ task: task(3), conversation_id: 'conversation-a',
    media: { kind: 'video', revision: 2, status: 'planning' } })))
  await Promise.all([first, duplicate])
  await vi.waitFor(() => expect((stream.details.value['task-a'].media as { revision: number }).revision).toBe(3))
  expect(reads).toBe(2)
})

it('replays a failed detail event instead of advancing its cursor and losing the update', async () => {
  const { stream } = await setup()
  vi.useFakeTimers()
  let failing = true
  vi.stubGlobal('fetch', async (url: string) => {
    if (url.startsWith('/api/v1/tasks/task-a') && failing) throw new Error('offline')
    return new Response(JSON.stringify({ task: task(4), conversation_id: 'conversation-a' }))
  })
  Events.all[0].emit('task.updated', { payload: { task_id: 'task-a', state_version: 4 } }, 'user:4')
  await vi.advanceTimersByTimeAsync(2500)
  expect(stream.details.value['task-a'].task.state_version).toBe(3)
  expect(Events.all[1].url).toBe('/api/v1/events')
  failing = false
  Events.all[1].emit('task.updated', { payload: { task_id: 'task-a', state_version: 4 } }, 'user:4')
  await vi.advanceTimersByTimeAsync(0)
  expect(stream.details.value['task-a'].task.state_version).toBe(4)
})

it('bounds stalled detail and authentication reads so subsequent events can recover', async () => {
  const { stream } = await setup()
  vi.useFakeTimers()
  vi.stubGlobal('fetch', () => new Promise<Response>(() => {}))
  Events.all[0].emit('task.updated', { payload: { task_id: 'task-a', state_version: 4 } }, 'user:4')
  await vi.advanceTimersByTimeAsync(32500)
  expect(Events.all).toHaveLength(2)
  expect(Events.all[0].closed).toBe(true)
  expect(stream.details.value['task-a'].task.state_version).toBe(3)
  vi.stubGlobal('fetch', async () => new Response(JSON.stringify({ task: task(4), conversation_id: 'conversation-a' })))
  Events.all[1].emit('task.updated', { payload: { task_id: 'task-a', state_version: 4 } }, 'user:4')
  await vi.advanceTimersByTimeAsync(0)
  expect(stream.details.value['task-a'].task.state_version).toBe(4)
})
