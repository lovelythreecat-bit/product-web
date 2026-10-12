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
      const result = await api.getProfile()
      if (epoch.value === version) changeIdentity(result, 'authenticated')
    } catch (e) {
      if (epoch.value === version) error.value = '暂时无法恢复登录，请重试或重新登录。'
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
  if (epoch.value === version && profile.value) account.value = result
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
export const session = { profile: readonly(profile), account: readonly(account), epoch: readonly(epoch), initialized: readonly(initialized), busy: readonly(busy), error: readonly(error), restore, authenticate, refreshAccount, saveProfile, logout }
