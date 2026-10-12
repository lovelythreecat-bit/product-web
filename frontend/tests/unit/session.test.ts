import { afterEach, describe, expect, it, vi } from 'vitest'
const alice = { user_id: 'alice', account: 'alice', nickname: 'Alice', bio: null, role: 'user' }
const bob = { user_id: 'bob', account: 'bob', nickname: null, bio: null, role: 'user' }
const balance = { available: 123, frozen: 8, consumed: 20, credited_total: 151 }
const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })
afterEach(() => { vi.unstubAllGlobals(); vi.resetModules() })
describe('session identity isolation', () => {
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
