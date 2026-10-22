import { afterEach, expect, it, vi } from 'vitest'
import { resumeWorkspace } from '../../src/features/workspace/resumeWorkspace'

const response = (value: unknown) => new Response(JSON.stringify(value))
afterEach(() => { vi.unstubAllGlobals() })

it('resolves the latest persisted task conversation on a fresh workspace entry using GET only', async () => {
  const fetch = vi.fn(async (url: string) => response(url.startsWith('/api/v1/tasks?') || url === '/api/v1/tasks'
    ? { items: [{ task_id: 'running-task' }], next_cursor: null }
    : { conversation_id: 'original-conversation' }))
  vi.stubGlobal('fetch', fetch)
  expect(await resumeWorkspace()).toBe('/workspace/original-conversation')
  expect(fetch.mock.calls.map(([url]) => url)).toEqual(['/api/v1/tasks?task_type=ordinary', '/api/v1/tasks/running-task'])
})

it('leaves accounts without tasks at the empty workspace', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => response({ items: [], next_cursor: null })))
  expect(await resumeWorkspace()).toBeUndefined()
})

it('keeps the workspace accessible when history cannot be read', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('offline') }))
  expect(await resumeWorkspace()).toBeUndefined()
})
