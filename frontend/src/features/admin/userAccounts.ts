import { onBeforeUnmount, ref, watch } from 'vue'
import { listUsers } from '../../api/admin'
import type { Schema } from '../../types/api'
import { session } from '../auth/session'

/** One directory per page; recursive record rendering never fetches users. */
export function useUserAccounts() {
  const users = ref<Schema<'AdminUserView'>[]>([])
  const loading = ref(false), error = ref('')
  const epoch = session.epoch.value
  let active = true
  let loaded = false
  let pending: Promise<void> | null = null
  const current = () => active && epoch === session.epoch.value
  onBeforeUnmount(() => { active = false })
  watch(() => session.epoch.value, () => { users.value = []; error.value = ''; loading.value = false })

  function remember(items: Schema<'AdminUserView'>[]) {
    if (!current()) return
    const known = new Map(users.value.map(user => [user.id, user]))
    for (const user of items) known.set(user.id, user)
    users.value = [...known.values()]
  }

  function load(firstPage?: Schema<'CursorPage_AdminUserView_'>): Promise<void> {
    if (!current()) return Promise.resolve()
    if (pending) return pending
    if (loaded) return Promise.resolve()
    loading.value = true
    error.value = ''
    pending = (async () => {
      try {
        const all: Schema<'AdminUserView'>[] = []
        const seen = new Set<string>()
        let cursor: string | undefined = firstPage?.next_cursor ?? undefined
        if (firstPage) all.push(...firstPage.items)
        if (firstPage && !cursor) {
          remember(all)
          loaded = true
          return
        }
        do {
          const page = await listUsers(cursor)
          if (!current()) return
          all.push(...page.items)
          cursor = page.next_cursor ?? undefined
          if (cursor && seen.has(cursor)) throw new Error('用户列表分页异常，请重新读取。')
          if (cursor) seen.add(cursor)
        } while (cursor)
        remember(all)
        loaded = true
      } catch {
        if (current()) error.value = '暂时无法读取账号列表，请刷新后重试。'
      } finally {
        if (current()) loading.value = false
        pending = null
      }
    })()
    return pending
  }

  function accountName(id: string | null | undefined, empty = '账号未提供') {
    if (!current()) return empty
    const profile = session.profile.value
    if (profile && id === profile.user_id && profile.account) return profile.account
    return users.value.find(user => user.id === id)?.account_normalized || empty
  }

  return { users, loading, error, load, remember, accountName }
}
