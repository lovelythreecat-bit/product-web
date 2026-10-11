import { describe, it, expect, vi, afterEach } from 'vitest'
const modules = import.meta.glob('../../src/api/client.ts')
async function client() {
  expect(Object.keys(modules), '同源安全 API client 尚未接入').toHaveLength(1)
  return await Object.values(modules)[0]() as typeof import('../../src/api/client')
}
afterEach(() => { vi.unstubAllGlobals(); document.cookie = 'csrf_token=; Max-Age=0' })
describe('same-origin API boundary', () => {
  it('sends cookie CSRF and keeps an intent immutable across explicit retries', async () => {
    const api = await client()
    document.cookie = 'csrf_token=TEST_ONLY_csrf'
    const seen: RequestInit[] = []
    vi.stubGlobal('fetch', async (_url: string, init: RequestInit) => {
      seen.push(init)
      if (seen.length === 1) throw new TypeError('network with internal secret')
      return new Response(JSON.stringify({ accepted: true }), { status: 200 })
    })
    const input = { instruction: 'original' }
    const intent = api.createIntent(input)
    input.instruction = 'edited'
    await expect(api.sendIntent('/api/v1/tasks', intent)).rejects.toMatchObject({ message: '网络连接失败，请核查原请求状态。' })
    expect(seen).toHaveLength(1)
    await api.sendIntent('/api/v1/tasks', intent)
    expect(seen[0].body).toBe('{"instruction":"original"}')
    expect(seen[1].body).toBe(seen[0].body)
    const headers = new Headers(seen[0].headers)
    expect(headers.get('Idempotency-Key')).toBe(new Headers(seen[1].headers).get('Idempotency-Key'))
    expect(headers.get('X-CSRF-Token')).toBe('TEST_ONLY_csrf')
    expect(headers.get('X-Requested-With')).toBe('platform')
    expect(headers.has('Origin')).toBe(false)
    expect(seen[0].credentials).toBe('same-origin')
  })
  it('rejects foreign URLs before sending and leaves FormData boundary to browser', async () => {
    const api = await client()
    const fetcher = vi.fn(async (_url: string, _init: RequestInit) => new Response('{}'))
    vi.stubGlobal('fetch', fetcher)
    await expect(api.request('https://evil.example/api', { method: 'GET' })).rejects.toThrow()
    await expect(api.request('//evil.example/api', { method: 'GET' })).rejects.toThrow()
    expect(fetcher).not.toHaveBeenCalled()
    const body = new FormData(); body.append('file', new Blob(['x']), 'test.txt')
    await api.request('/api/v1/files', { method: 'POST', body })
    expect(new Headers(fetcher.mock.calls[0][1].headers).has('Content-Type')).toBe(false)
  })
  it('only exposes public ErrorResponse and hides unstructured server errors', async () => {
    const api = await client()
    vi.stubGlobal('fetch', async () => new Response('secret /internal/path', {status:500}))
    await expect(api.request('/api/v1/tasks')).rejects.toMatchObject({ message: '请求暂时无法完成，请稍后查询。' })
    vi.stubGlobal('fetch', async () => new Response(JSON.stringify({error:{code:'FEATURE_NOT_ENABLED',message:'当前功能尚未启用。',current_quotes:null,current_specs:null},trace_id:'1e790eac-f72d-4114-8e57-52ad60c7609b'}), {status:403}))
    await expect(api.request('/api/v1/tasks')).rejects.toMatchObject({ message: '当前功能尚未启用。', code:'FEATURE_NOT_ENABLED' })
  })
})