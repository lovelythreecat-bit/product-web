import { afterEach, describe, expect, it, vi } from 'vitest'
import * as files from '../../src/api/files'
import { ApiError, setIdentityBoundary } from '../../src/api/client'

afterEach(() => { setIdentityBoundary(undefined); vi.unstubAllGlobals() })

describe('private file reads', () => {
  it('returns the authenticated file bytes', async () => {
    const picture = new Blob(['picture'], { type: 'image/png' })
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, blob: async () => picture })))
    const blob = await files.getFileContentBlob('file-1')
    const content = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result))
      reader.onerror = reject
      reader.readAsText(blob)
    })
    expect(content).toBe('picture')
    expect(blob.type).toBe('image/png')
  })

  it('revokes the current session on a file 401', async () => {
    const unauthorized = vi.fn()
    setIdentityBoundary({ epoch: () => 1, unauthorized })
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 401 })))
    await expect(files.getFileContentBlob('file-1')).rejects.toMatchObject({ status: 401 })
    expect(unauthorized).toHaveBeenCalledOnce()
  })

  it('rejects a late response without revoking the new identity', async () => {
    let epoch = 1
    const unauthorized = vi.fn()
    setIdentityBoundary({ epoch: () => epoch, unauthorized })
    vi.stubGlobal('fetch', vi.fn(async () => { epoch = 2; return new Response('{}', { status: 401 }) }))
    await expect(files.getFileContentBlob('file-1')).rejects.toMatchObject({ code: 'IDENTITY_CHANGED' })
    expect(unauthorized).not.toHaveBeenCalled()
  })

  it('rejects file bytes that finish reading after an identity change', async () => {
    let epoch = 1
    setIdentityBoundary({ epoch: () => epoch, unauthorized: vi.fn() })
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, blob: async () => { epoch = 2; return new Blob(['old-picture']) } })))
    await expect(files.getFileContentBlob('file-1')).rejects.toMatchObject({ code: 'IDENTITY_CHANGED' })
  })

  it('propagates cancellation as a failed private read', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new DOMException('aborted', 'AbortError') }))
    await expect(files.getFileContentBlob('file-1', new AbortController().signal)).rejects.toBeInstanceOf(ApiError)
  })
})
