import { createIntent, type Intent } from '../../api/client'
import type { Schema } from '../../types/api'
import { onIdentityChange } from '../auth/session'
const prefix = 'admin-credit-intent:v1:'
export type CreditIntent = Intent<Schema<'CreditGrantRequest'>>
export function restoreGrant(actor: string): CreditIntent | null {
  const raw = localStorage.getItem(prefix + actor)
  if (!raw) return null
  const value = JSON.parse(raw) as CreditIntent
  const input = JSON.parse(value.body) as Schema<'CreditGrantRequest'>
  if (!value.key || input.business_key !== value.key || !input.user_id || !Number.isSafeInteger(input.amount) || input.amount < 0 || !input.reason?.trim()) throw new Error('待核对发放记录无法读取，请保留本地记录并联系维护人员核对。')
  return Object.freeze({key:value.key,body:value.body})
}
export function rememberGrant(actor: string, input: Omit<Schema<'CreditGrantRequest'>,'business_key'>): CreditIntent {
  const existing = restoreGrant(actor)
  if (existing) throw new Error('有一笔发放等待核对，请先处理原请求。')
  const key = crypto.randomUUID()
  const intent = createIntent({...input,business_key:key},key)
  localStorage.setItem(prefix + actor,JSON.stringify(intent))
  return intent
}
export function forgetGrant(actor: string, key: string) {
  // A replay finishing in another tab must not erase a newer confirmed intent.
  if (restoreGrant(actor)?.key === key) localStorage.removeItem(prefix + actor)
}
// Refresh restores the same actor's pending intent; logout, 401 and a different actor erase private data.
onIdentityChange(change => {
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const key = localStorage.key(i)
    if (key?.startsWith(prefix) && (change.reason !== 'authenticated' || key !== prefix + change.userId)) localStorage.removeItem(key)
  }
})
