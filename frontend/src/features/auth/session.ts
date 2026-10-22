import { readonly, ref } from 'vue'
import * as api from '../../api/auth'
import { getAccount } from '../../api/account'
import { ApiError, setIdentityBoundary } from '../../api/client'
import type { Schema } from '../../types/api'

const profile = ref<Schema<'ProfileView'> | null>(null)
const account = ref<Schema<'AccountView'> | null>(null)
const epoch = ref(0)
const initialized = ref(false)
const busy = ref(false)
const error = ref('')
type IdentityChange = { epoch: number; userId: string | null; reason: 'authenticated' | 'logout' | 'unauthorized' }
const listeners = new Set<(change: IdentityChange) => void>()
let restoring: Promise<void> | undefined

function changeIdentity(next: Schema<'ProfileView'> | null, reason: IdentityChange['reason']) {
  epoch.value++
  profile.value = next
  account.value = null
  initialized.value = true
  restoring = undefined
  for (const listener of listeners) listener({ epoch: epoch.value, userId: next?.user_id ?? null, reason })
}
/** T18c: subscribe synchronously to close streams and clear ALL user-scoped caches/cursors. */
export function onIdentityChange(listener: (change: IdentityChange) => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}
setIdentityBoundary({ epoch: () => epoch.value, unauthorized: () => changeIdentity(null, 'unauthorized') })

async function restore() {
  if (initialized.value) return
  if (restoring) return restoring
  const version = epoch.value
  const pending = (async () => {
    error.value = ''
    try {
      // A failed profile read is not proof that the cookie session expired.
      // Keep the navigation guard pending for one bounded retry before giving up.
      for (let attempt = 0; attempt < 2 && epoch.value === version; attempt++) {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 5000)
        try {
          const result = await api.getProfile(controller.signal)
          if (epoch.value === version) changeIdentity(result, 'authenticated')
          return
        } catch (e) {
          if (epoch.value !== version) return
          const recoverable = controller.signal.aborted || e instanceof ApiError && (e.status === 0 || e.status >= 500)
          if (attempt === 0 && recoverable) {
            await new Promise(resolve => setTimeout(resolve, 250))
          } else {
            error.value = '暂时无法恢复登录，请重试或重新登录。'
            return
          }
        } finally { clearTimeout(timeout) }
      }
    } finally { if (epoch.value === version) restoring = undefined }
  })()
  restoring = pending
  return pending
}
async function authenticate(body: Schema<'LoginRequest'> | Schema<'RegisterRequest'>) {
  if (busy.value) return false
  busy.value = true
  const version = epoch.value
  try {
    const result = 'request_key' in body ? await api.register(body) : await api.login(body)
    if (epoch.value !== version) return false
    changeIdentity(result.profile, 'authenticated')
    error.value = ''
    return true
  } finally { busy.value = false }
}
async function refreshAccount() {
  const version = epoch.value
  const result = await getAccount()
  if (epoch.value === version && profile.value && (
    !account.value || account.value.available !== result.available ||
    account.value.frozen !== result.frozen || account.value.consumed !== result.consumed ||
    account.value.credited_total !== result.credited_total
  )) account.value = result
  return result
}
async function saveProfile(body: Schema<'ProfileUpdate'>) {
  const version = epoch.value
  const result = await api.updateProfile(body)
  if (epoch.value === version && profile.value?.user_id === result.user_id) profile.value = result
}
async function logout() {
  if (busy.value) return false
  busy.value = true
  try {
    await api.logout()
    changeIdentity(null, 'logout')
    return true
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return true
    throw e
  } finally { busy.value = false }
}
async function changePassword(body: Schema<'PasswordChangeRequest'>) {
  if (busy.value) return false
  busy.value = true
  const version = epoch.value
  try {
    await api.changePassword(body)
    if (version !== epoch.value) return false
    changeIdentity(null, 'logout')
    return true
  } finally { busy.value = false }
}
export const session = { profile: readonly(profile), account: readonly(account), epoch: readonly(epoch), initialized: readonly(initialized), busy: readonly(busy), error: readonly(error), restore, authenticate, refreshAccount, saveProfile, logout, changePassword }
