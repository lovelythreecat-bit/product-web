import { describe, expect, it, vi } from 'vitest'
import { installRandomUUID } from '../../src/compat/randomUUID'

describe('HTTP deployment UUID support', () => {
  it('uses cryptographic random bytes and the UUID v4 version/variant', () => {
    const getRandomValues = vi.fn((bytes: Uint8Array) => {
      bytes.fill(255)
      return bytes
    })
    const cryptoApi = { getRandomValues } as unknown as Crypto
    installRandomUUID(cryptoApi)
    expect(cryptoApi.randomUUID()).toBe('ffffffff-ffff-4fff-bfff-ffffffffffff')
    expect(getRandomValues).toHaveBeenCalledOnce()
  })

  it('keeps a native implementation unchanged', () => {
    const native = vi.fn(() => 'native')
    const cryptoApi = { randomUUID: native } as unknown as Crypto
    installRandomUUID(cryptoApi)
    expect(cryptoApi.randomUUID).toBe(native)
  })

  it('draws new random bytes for each invocation', () => {
    let invocation = 0
    const cryptoApi = { getRandomValues: (bytes: Uint8Array) => bytes.fill(++invocation) } as unknown as Crypto
    installRandomUUID(cryptoApi)
    expect(cryptoApi.randomUUID()).not.toBe(cryptoApi.randomUUID())
  })
})
