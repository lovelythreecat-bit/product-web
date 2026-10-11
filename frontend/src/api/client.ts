import type { components } from '../types/contracts'
type PublicError = components['schemas']['ErrorResponse']
export class ApiError extends Error {
  constructor(message: string, public status = 0, public code?: string, public response?: PublicError) { super(message); this.name = 'ApiError' }
}
export interface Intent<T> { readonly key: string; readonly body: string; readonly inputType?: T }
/** Create once per confirmed intent; retries retain this serialized body and key. */
export function createIntent<T>(input: T, key: string = crypto.randomUUID()): Intent<T> {
  return Object.freeze({ key, body: JSON.stringify(input) })
}
function csrfToken(): string {
  const value = document.cookie.split(';').map(part => part.trim()).find(part => part.startsWith('csrf_token='))
  try { return value ? decodeURIComponent(value.slice(11)) : '' } catch { return '' }
}
export async function request<T>(path: string, options: {method?: 'GET'|'POST'|'PATCH'|'DELETE'; body?: string|FormData|Blob; key?: string; signal?: AbortSignal} = {}): Promise<T> {
  if (!path.startsWith('/api/v1/') || path.includes('\\') || new URL(path, location.origin).origin !== location.origin) throw new ApiError('仅允许同源平台接口。')
  const method = options.method ?? 'GET'
  const headers = new Headers({ Accept:'application/json' })
  if (method !== 'GET') {
    headers.set('X-Requested-With', 'platform')
    const csrf = csrfToken(); if (csrf) headers.set('X-CSRF-Token', csrf)
  }
  if (options.body instanceof Blob && options.body.type) headers.set('Content-Type', options.body.type)
  if (typeof options.body === 'string') headers.set('Content-Type', 'application/json')
  if (options.key) headers.set('Idempotency-Key', options.key)
  let response: Response
  try { response = await fetch(path, {method, headers, body:options.body, signal:options.signal, credentials:'same-origin', redirect:'error'}) }
  catch { throw new ApiError('网络连接失败，请核查原请求状态。') }
  if (response.status === 204) return undefined as T
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const publicError = payload as PublicError | null
    if (publicError?.error && typeof publicError.error.code === 'string' && typeof publicError.error.message === 'string')
      throw new ApiError(publicError.error.message, response.status, publicError.error.code, publicError)
    throw new ApiError('请求暂时无法完成，请稍后查询。', response.status)
  }
  if (payload === null) throw new ApiError('服务返回的数据暂时无法读取。', response.status)
  return payload as T
}
export function sendIntent<T, R>(path: string, intent: Intent<T>): Promise<R> { return request<R>(path, {method:'POST', body:intent.body, key:intent.key}) }
export function jsonRequest<T>(path: string, method: 'POST'|'PATCH'|'DELETE', body: unknown): Promise<T> { return request<T>(path, {method, body:JSON.stringify(body)}) }
export function query(values: Record<string, string|number|undefined>): string {
  const params = new URLSearchParams(); for (const [key,value] of Object.entries(values)) if (value !== undefined) params.set(key,String(value))
  return params.size ? '?' + params.toString() : ''
}
export const id = encodeURIComponent
