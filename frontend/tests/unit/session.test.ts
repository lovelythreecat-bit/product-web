import { afterEach, describe, expect, it, vi } from 'vitest'
const alice = { user_id: 'alice', account: 'alice', nickname: 'Alice', bio: null, role: 'user' }
const bob = { user_id: 'bob', account: 'bob', nickname: null, bio: null, role: 'user' }
const balance = { available: 123, frozen: 8, consumed: 20, credited_total: 151 }
const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.resetModules() })
describe('session identity isolation', () => {
  it.each(['server', 'network'])('recovers the initial identity before navigation continues after a transient %s failure', async failure => {
    const fetch = vi.fn().mockImplementationOnce(async () => {
      if (failure === 'network') throw new Error('offline')
      return response({}, 500)
    }).mockResolvedValue(response(alice))
    vi.stubGlobal('fetch', fetch)
    const { session } = await import('../../src/features/auth/session')
    await Promise.all([session.restore(), session.restore()])
    expect(session.profile.value?.user_id).toBe('alice')
    expect(session.initialized.value).toBe(true)
    expect(session.error.value).toBe('')
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(fetch.mock.calls.every(([path]) => path === '/api/v1/me')).toBe(true)
  })
  it('does not retry an expired or revoked session', async () => {
    const fetch = vi.fn(async () => response({}, 401))
    vi.stubGlobal('fetch', fetch)
    const { session } = await import('../../src/features/auth/session')
    await session.restore()
    expect(session.profile.value).toBeNull()
    expect(session.initialized.value).toBe(true)
    expect(fetch).toHaveBeenCalledOnce()
  })
  it('stops restoring after two transient failures and keeps the credential eligible for a later read', async () => {
    const fetch = vi.fn(async () => response({}, 503))
    vi.stubGlobal('fetch', fetch)
    const { session } = await import('../../src/features/auth/session')
    await session.restore()
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(session.initialized.value).toBe(false)
    expect(session.error.value).not.toBe('')
  })
  it('aborts a stalled initial read and restores with the bounded retry', async () => {
    const signals: AbortSignal[] = []
    const fetch = vi.fn().mockImplementationOnce((_path, options: RequestInit) => {
      const signal = options.signal!
      signals.push(signal)
      return new Promise<Response>((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('aborted'))))
    }).mockResolvedValue(response(alice))
    vi.stubGlobal('fetch', fetch)
    const { session } = await import('../../src/features/auth/session')
    vi.useFakeTimers()
    const restored = session.restore()
    await vi.advanceTimersByTimeAsync(5500)
    expect(signals[0].aborted).toBe(true)
    expect(fetch).toHaveBeenCalledTimes(2)
    await restored
    expect(session.profile.value?.user_id).toBe('alice')
    expect(vi.getTimerCount()).toBe(0)
  })
  it('cancels a pending restore retry when another identity is authenticated', async () => {
    const fetch = vi.fn(async (path: string) => path.endsWith('/login')
      ? response({ profile: bob, replayed: false }) : response({}, 500))
    vi.stubGlobal('fetch', fetch)
    const { session } = await import('../../src/features/auth/session')
    vi.useFakeTimers()
    const restored = session.restore()
    await vi.advanceTimersByTimeAsync(0)
    await session.authenticate({ account: 'bob', password: 'TEST_ONLY_password' })
    await vi.advanceTimersByTimeAsync(300)
    await restored
    expect(fetch.mock.calls.filter(([path]) => path === '/api/v1/me')).toHaveLength(1)
    expect(session.profile.value?.user_id).toBe('bob')
    expect(vi.getTimerCount()).toBe(0)
  })
  it('keeps account identity stable for unchanged balances so sidebar watchers stay idle', async () => {
    let current = balance
    vi.stubGlobal('fetch', async (path: string) => response(path.endsWith('/me') ? alice : current))
    const { session } = await import('../../src/features/auth/session')
    await session.restore(); await session.refreshAccount()
    const first = session.account.value
    await session.refreshAccount()
    expect(session.account.value).toBe(first)
    current = { ...balance, available: 124, credited_total: 152 }
    await session.refreshAccount()
    expect(session.account.value).not.toBe(first)
    expect(session.account.value?.available).toBe(124)
  })
  it('keeps a restored identity and balance after transient server or network errors', async () => {
    let failure = 0
    vi.stubGlobal('fetch', async (path: string) => {
      if (failure === 1) return response({}, 500)
      if (failure === 2) throw new Error('offline')
      return response(path.endsWith('/me') ? alice : balance)
    })
    const { session } = await import('../../src/features/auth/session')
    await session.restore(); await session.refreshAccount()
    const version = session.epoch.value
    for (failure = 1; failure <= 2; failure++) {
      await expect(session.refreshAccount()).rejects.toBeInstanceOf(Error)
      expect(session.profile.value?.user_id).toBe('alice')
      expect(session.account.value).toEqual(balance)
      expect(session.epoch.value).toBe(version)
    }
  })
  it('clears profile, account and identity caches only after a successful password change', async () => {
    let reject = true
    vi.stubGlobal('fetch', async (path: string) => path.endsWith('/me') ? response(alice) : path.endsWith('/account') ? response(balance) : reject ? response({ error: { code: 'INPUT_INVALID', message: '当前密码不正确。' } }, 400) : new Response(null, { status: 204 }))
    const { session, onIdentityChange } = await import('../../src/features/auth/session')
    await session.restore(); await session.refreshAccount()
    const changed = vi.fn(); const stop = onIdentityChange(changed)
    const body = { current_password: 'old-password', new_password: 'new-password' }
    await expect(session.changePassword(body)).rejects.toMatchObject({ status: 400 })
    expect(session.profile.value?.user_id).toBe('alice'); expect(changed).not.toHaveBeenCalled()
    reject = false; expect(await session.changePassword(body)).toBe(true)
    expect(session.profile.value).toBeNull(); expect(session.account.value).toBeNull(); expect(changed).toHaveBeenCalledOnce(); stop()
  })
  it('restores once with GET me and clears account plus subscriber cursors on logout', async () => {
    const paths: string[] = []
    vi.stubGlobal('fetch', async (path: string) => {
      paths.push(path)
      return path.endsWith('/me') ? response(alice) : path.endsWith('/account') ? response(balance) : new Response(null, { status: 204 })
    })
    const { session, onIdentityChange } = await import('../../src/features/auth/session')
    let cursor = 'alice:cursor'
    const stop = onIdentityChange(() => { cursor = '' })
    await Promise.all([session.restore(), session.restore()])
    expect(paths.filter(p => p.endsWith('/me'))).toHaveLength(1)
    expect(session.profile.value?.user_id).toBe('alice')
    await session.refreshAccount()
    expect(session.account.value).toEqual(balance)
    cursor = 'alice:new'
    await session.logout()
    expect(session.profile.value).toBeNull()
    expect(session.account.value).toBeNull()
    expect(cursor).toBe('')
    stop()
  })
  it('rejects late success and late 401 from previous identity without clearing new user', async () => {
    const pending: ((r: Response) => void)[] = []
    vi.stubGlobal('fetch', async (path: string) => {
      if (path.endsWith('/me')) return response(alice)
      if (path.endsWith('/account')) return new Promise<Response>(resolve => pending.push(resolve))
      if (path.endsWith('/login')) return response({ profile: bob, replayed: false })
      return new Response(null, { status: 204 })
    })
    const { session } = await import('../../src/features/auth/session')
    await session.restore()
    const oldSuccess = session.refreshAccount().catch(e => e.code)
    const oldUnauthorized = session.refreshAccount().catch(e => e.code)
    await session.logout()
    await session.authenticate({ account: 'bob', password: 'TEST_ONLY_password' })
    pending[0](response(balance)); pending[1](response({}, 401))
    expect(await oldSuccess).toBe('IDENTITY_CHANGED')
    expect(await oldUnauthorized).toBe('IDENTITY_CHANGED')
    expect(session.profile.value?.user_id).toBe('bob')
    expect(session.account.value).toBeNull()
  })
  it('401 clears restored profile and balance before notifying consumers', async () => {
    let expire = false
    vi.stubGlobal('fetch', async (path: string) => path.endsWith('/me') ? response(alice) : response(expire ? {} : balance, expire ? 401 : 200))
    const { session, onIdentityChange } = await import('../../src/features/auth/session')
    await session.restore(); await session.refreshAccount()
    const cleared: boolean[] = []
    onIdentityChange(e => { if (e.reason === 'unauthorized') cleared.push(session.profile.value === null && session.account.value === null) })
    expire = true
    await expect(session.refreshAccount()).rejects.toMatchObject({ status: 401 })
    expect(cleared).toEqual([true])
  })
})
