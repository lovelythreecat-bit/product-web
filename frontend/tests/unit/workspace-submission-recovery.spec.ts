import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { reactive, ref } from 'vue'
import { createIntent } from '../../src/api/client'
import type { Schema } from '../../src/types/api'

const route = reactive({ params: { conversationId: 'recovery' } })
const refreshTask = vi.fn(async () => {}), reconnect = vi.fn(async () => {})
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push: vi.fn() }) }))
vi.mock('../../src/features/auth/session', () => ({
  session: { epoch: ref(1), profile: ref({ user_id: 'recovery-user' }), refreshAccount: vi.fn(async () => {}) },
  onIdentityChange: () => () => {},
}))
vi.mock('../../src/features/workspace/useTaskStream', () => ({ useTaskStream: () => ({
  tasks: ref([]), details: ref({}), fragments: ref({}), connectionState: ref('open'), refreshTask, reconnect,
}) }))
vi.mock('../../src/api/catalog', () => ({ listAgents: vi.fn(async () => []), listSpecs: vi.fn(async () => []), quote: vi.fn() }))

import WorkspaceView from '../../src/features/workspace/WorkspaceView.vue'
import { draftFor } from '../../src/features/workspace/drafts'

const body = {
  conversation_id: 'recovery', agent_id: 'agent',
  input: { product_version: 'product-v1', product: { name: 'cup' }, instruction: 'fixed', parameters: {}, material_versions: [] },
  confirmed_quote: { credits: 8, spec_id: 'spec', spec_version: 's1', price_version: 'p1', agent_version: 'a1', policy_versions: {}, input_digest: 'fixed' },
} as Schema<'SubmitTaskRequest'>
const wrappers: VueWrapper[] = []
function open() {
  const wrapper = mount(WorkspaceView, { global: { stubs: {
    AgentSelector: true, SpecForm: true, QuotePanel: true, TaskCard: true, PromptEditor: true, AppDrawer: true,
    AppDialog: { props: ['open'], template: '<div v-if="open"><slot/><slot name="actions"/></div>' },
  } } })
  wrappers.push(wrapper)
  return wrapper
}
function submit(wrapper: VueWrapper) { return (wrapper.vm as unknown as { submit(): Promise<void> }).submit() }
const recoveryButton = (wrapper: VueWrapper) => wrapper.findAll('button').find(button => button.text() === '核对并重试原请求')
beforeEach(() => {
  const draft = draftFor('recovery')
  draft.confirmed = body; draft.pending = null; draft.uncertain = false
  refreshTask.mockClear(); reconnect.mockClear()
})
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()); vi.unstubAllGlobals() })

it.each([
  ['502 proxy response', () => new Response('bad gateway', { status: 502 })],
  ['504 proxy response', () => new Response('timeout', { status: 504 })],
  ['unreadable success JSON', () => new Response('{', { status: 201 })],
  ['success JSON without task', () => new Response('{}', { status: 201 })],
  ['success JSON without task ID', () => new Response('{"task":{}}', { status: 201 })],
] as const)('retains the exact charged intent after %s and replays it explicitly', async (_name, response) => {
  const fetch = vi.fn().mockResolvedValueOnce(response()).mockResolvedValueOnce(new Response('{"task":{"task_id":"original-task"}}', { status: 200 }))
  vi.stubGlobal('fetch', fetch)
  const wrapper = open()
  await submit(wrapper)
  await flushPromises()
  const retained = draftFor('recovery').pending
  expect(retained?.body).toBe(JSON.stringify(body))
  expect(recoveryButton(wrapper)?.exists()).toBe(true)
  await recoveryButton(wrapper)!.trigger('click')
  await flushPromises()
  expect(reconnect).toHaveBeenCalledTimes(1)
  expect(fetch).toHaveBeenCalledTimes(1)
  await submit(wrapper)
  expect(fetch).toHaveBeenCalledTimes(2)
  const first = fetch.mock.calls[0][1], second = fetch.mock.calls[1][1]
  expect(second.body).toBe(first.body)
  expect(second.headers.get('Idempotency-Key')).toBe(first.headers.get('Idempotency-Key'))
  expect(second.headers.get('Idempotency-Key')).toBe(retained!.key)
  expect(refreshTask).toHaveBeenCalledWith('original-task')
  expect(draftFor('recovery').pending).toBeNull()
})

it('ends the intent only for a structured, definitive admission rejection', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response('{"error":{"code":"INSUFFICIENT_CREDITS","message":"不足"}}', { status: 402 })))
  await submit(open())
  expect(draftFor('recovery').pending).toBeNull()
})

it('shows recovery for a persisted pending intent even when its old uncertain flag is false', async () => {
  const original = createIntent(body)
  draftFor('recovery').pending = original
  draftFor('recovery').uncertain = false
  const wrapper = open()
  await flushPromises()
  expect(recoveryButton(wrapper)?.exists()).toBe(true)
  expect(draftFor('recovery').pending).toEqual(original)
})

it('leaving during POST and returning while the old request is unresolved permits only original-intent recovery', async () => {
  let finish!: (response: Response) => void
  const fetch = vi.fn().mockImplementationOnce(() => new Promise<Response>(resolve => { finish = resolve }))
    .mockResolvedValueOnce(new Response('{"task":{"task_id":"original-task"}}'))
  vi.stubGlobal('fetch', fetch)
  const first = open(), inFlight = submit(first)
  const original = draftFor('recovery').pending
  expect(original).toBeTruthy()
  first.unmount()
  const returned = open()
  await flushPromises()
  expect(recoveryButton(returned)?.exists()).toBe(true)
  await recoveryButton(returned)!.trigger('click')
  await flushPromises()
  expect(fetch).toHaveBeenCalledTimes(1)
  await submit(returned)
  expect(fetch.mock.calls[1][1].headers.get('Idempotency-Key')).toBe(original!.key)
  expect(fetch.mock.calls[1][1].body).toBe(original!.body)
  finish(new Response('bad gateway', { status: 502 }))
  await inFlight
  expect(draftFor('recovery').pending).toBeNull()
  expect(refreshTask).toHaveBeenCalledTimes(1)
})
