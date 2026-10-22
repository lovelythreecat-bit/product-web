import { onScopeDispose, ref, shallowRef, toValue, watch, type MaybeRefOrGetter } from 'vue'
import { getConversation } from '../../api/conversations'
import { getTask, listTasks } from '../../api/tasks'
import { getProfile } from '../../api/auth'
import { connectTaskEvents, type Schema } from '../../types/api'
import { onIdentityChange, session } from '../auth/session'
import { taskMedia } from '../../types/media'

/** One owner per mounted conversation. Reconnects reconcile persisted originals; never submit. */
export function useTaskStream(conversationId: MaybeRefOrGetter<string>) {
  const tasks = shallowRef<Schema<'TaskView'>[]>([])
  const latestTaskId = ref('')
  const details = shallowRef<Record<string, Schema<'TaskDetail'>>>({})
  const fragments = ref<Record<string, string>>({})
  const connectionState = ref<'connecting' | 'open' | 'recovering' | 'closed'>('closed')
  const error = ref('')
  let source: EventSource | undefined, timer: ReturnType<typeof setTimeout> | undefined
  let cursor = '', revision = 0, disposed = false, retryAttempt = 0
  let listedOrder: string[] = []
  const requests = new Map<string, { revision: number; promise: Promise<void> }>()
  const reads = new Set<AbortController>()
  const unrelatedTasks = new Set<string>()
  const terminal = (state: string) => ['SUCCEEDED', 'FAILED', 'MANUALLY_CLOSED'].includes(state)
  function close() {
    source?.close(); source = undefined; clearTimeout(timer); timer = undefined
    for (const controller of reads) controller.abort()
    reads.clear()
  }
  function read<T>(operation: (signal: AbortSignal) => Promise<T>): Promise<T> {
    const controller = new AbortController()
    reads.add(controller)
    const timeout = setTimeout(() => controller.abort(), 15000)
    return new Promise<T>((resolve, reject) => {
      controller.signal.addEventListener('abort', () => reject(new Error('Task read interrupted')), { once: true })
      operation(controller.signal).then(resolve, reject)
    }).finally(() => { clearTimeout(timeout); reads.delete(controller) })
  }
  function token() { return { revision, epoch: session.epoch.value, id: toValue(conversationId) } }
  function current(t: ReturnType<typeof token>) { return !disposed && t.revision === revision && t.epoch === session.epoch.value && t.id === toValue(conversationId) }
  function merge(detail: Schema<'TaskDetail'>) {
    if (detail.conversation_id !== toValue(conversationId)) return
    const previous = tasks.value.find(t => t.task_id === detail.task.task_id)
    if (previous && previous.state_version > detail.task.state_version) return
    const oldDetail = details.value[detail.task.task_id]
    if (oldDetail && previous?.state_version === detail.task.state_version &&
        (taskMedia(oldDetail)?.revision ?? -1) > (taskMedia(detail)?.revision ?? -1)) return
    if (oldDetail && JSON.stringify(oldDetail) === JSON.stringify(detail)) return
    details.value = { ...details.value, [detail.task.task_id]: detail }
    const merged = previous ? tasks.value.map(t => t.task_id === detail.task.task_id ? detail.task : t) : [detail.task, ...tasks.value]
    tasks.value = merged.sort((a, b) => {
      const time = (value: Schema<'TaskView'>) => Date.parse(value.created_at || '') || 0
      const byTime = time(b) - time(a)
      if (byTime) return byTime
      const aRank = listedOrder.indexOf(a.task_id), bRank = listedOrder.indexOf(b.task_id)
      if (aRank !== bRank) return (aRank < 0 ? -1 : aRank) - (bRank < 0 ? -1 : bRank)
      return a.task_id === b.task_id ? 0 : a.task_id < b.task_id ? 1 : -1
    })
    // A listed newest task may still be awaiting its detail response.
    if (!latestTaskId.value || details.value[latestTaskId.value]) latestTaskId.value = tasks.value[0]?.task_id || ''
    if (['SUCCEEDED', 'FAILED', 'MANUALLY_CLOSED'].includes(detail.task.state)) delete fragments.value[detail.task.task_id]
  }
  function refreshTask(id: string, t = token()): Promise<void> {
    const pending = requests.get(id)
    if (pending?.revision === t.revision) return pending.promise
    const request = { revision: t.revision, promise: Promise.resolve() }
    request.promise = read(signal => getTask(id, signal)).then(detail => {
      if (!current(t)) return
      if (detail.conversation_id !== t.id) unrelatedTasks.add(id)
      else merge(detail)
    })
      .finally(() => { if (requests.get(id) === request) requests.delete(id) })
    requests.set(id, request)
    return request.promise
  }
  async function reconcile(t: ReturnType<typeof token>) {
    await read(signal => getConversation(t.id, signal))
    if (!current(t)) return
    const listed: Schema<'TaskView'>[] = []
    let next: string | undefined
    do {
      const page = await read(signal => listTasks(t.id, next, signal))
      if (!current(t)) return
      listed.push(...page.items); next = page.next_cursor ?? undefined
    } while (next)
    // The list is creation-ordered; parallel detail responses are not.
    latestTaskId.value = listed[0]?.task_id || ''
    listedOrder = listed.map(task => task.task_id)
    const changed = listed.filter(task => {
      const known = details.value[task.task_id]
      return !known || known.task.state_version < task.state_version || !terminal(task.state)
    })
    // Bound admission pressure when opening a long history. Completed cached results
    // stay mounted; task.work_ids already identifies independently durable works.
    let index = 0
    await Promise.all(Array.from({ length: Math.min(4, changed.length) }, async () => {
      while (current(t) && index < changed.length) await refreshTask(changed[index++].task_id, t)
    }))
  }
  function open(t: ReturnType<typeof token>) {
    if (!current(t)) return
    const owned = connectTaskEvents(cursor || undefined); source = owned
    const live = () => current(t) && source === owned
    let events = Promise.resolve()
    owned.onopen = () => { if (live()) connectionState.value = 'open' }
    owned.addEventListener('task.updated', event => {
      if (!live()) return
      const e = event as MessageEvent
      events = events.then(async () => {
        if (!live()) return
        const durable = JSON.parse(e.data) as Schema<'DurableEventView'>
        if (!durable.payload?.task_id) return
        const payload = durable.payload
        if (!unrelatedTasks.has(payload.task_id) && (!payload.conversation_id || payload.conversation_id === t.id)) {
          const known = details.value[payload.task_id]
          const caughtUp = () => known && known.task.state_version >= payload.state_version &&
            (payload.media_revision == null || (taskMedia(known)?.revision ?? -1) >= payload.media_revision)
          if (!caughtUp()) {
            // A manual GET may already be in flight when this notification arrives.
            // If its snapshot predates this event, follow it with one fresh read.
            const pending = requests.get(payload.task_id)?.revision === t.revision
            await refreshTask(payload.task_id, t)
            const updated = details.value[payload.task_id]
            if (pending && live() && updated && (updated.task.state_version < payload.state_version ||
                (payload.media_revision != null && (taskMedia(updated)?.revision ?? -1) < payload.media_revision))) {
              await refreshTask(payload.task_id, t)
            }
          }
        }
        // Commit cursors in event order only after persisted state was read successfully.
        if (live()) { if (e.lastEventId) cursor = e.lastEventId; retryAttempt = 0 }
      }).catch(() => { if (live()) void retryStream(t) })
    })
    owned.addEventListener('transient_fragment', event => {
      if (!live()) return
      try {
        const fragment = JSON.parse((event as MessageEvent).data) as Schema<'TransientFragment'>
        if (details.value[fragment.task_id] && !['SUCCEEDED', 'FAILED', 'MANUALLY_CLOSED'].includes(details.value[fragment.task_id].task.state)) fragments.value[fragment.task_id] = fragment.text
      } catch { /* A transient fragment cannot affect persisted state or its cursor. */ }
    })
    owned.addEventListener('reset', event => {
      if (!live()) return
      events = events.then(async () => {
        if (!live()) return
        cursor = (event as MessageEvent).lastEventId
        await reconnect()
      }).catch(() => { if (live()) void retryStream(t) })
    })
    owned.onerror = () => { if (live()) void retryStream(t) }
  }
  async function retryStream(t: ReturnType<typeof token>) {
    if (!current(t)) return
    close()
    connectionState.value = 'recovering'
    const delay = Math.min(30000, 2500 * 2 ** Math.min(retryAttempt++, 4))
    // EventSource errors hide HTTP status. An ordinary protected GET detects a real
    // expired login without clearing user data on transient transport/server errors.
    try { await read(signal => getProfile(signal)) } catch { /* The shared client handles genuine 401s. */ }
    if (current(t)) timer = setTimeout(() => { if (current(t)) open(t) }, delay)
  }
  async function recover() {
    close()
    revision++
    const t = token()
    if (!t.id || disposed) { connectionState.value = 'closed'; return }
    connectionState.value = 'recovering'; error.value = ''
    try {
      await reconcile(t)
      if (!current(t)) return
      connectionState.value = 'connecting'
      open(t)
    } catch {
      if (!current(t)) return
      error.value = '连接暂时中断，正在核对原任务。'; connectionState.value = 'recovering'
      const delay = Math.min(30000, 2500 * 2 ** Math.min(retryAttempt++, 4))
      timer = setTimeout(() => { if (current(t)) void reconnect() }, delay)
    }
  }
  function reconnect() { return recover() }
  function clear() { revision++; close(); requests.clear(); unrelatedTasks.clear(); cursor = ''; retryAttempt = 0; listedOrder = []; latestTaskId.value = ''; tasks.value = []; details.value = {}; fragments.value = {}; error.value = ''; connectionState.value = 'closed' }
  const unsubscribe = onIdentityChange(clear)
  watch(() => toValue(conversationId), () => { clear(); void reconnect() }, { immediate: true, flush: 'sync' })
  onScopeDispose(() => { disposed = true; clear(); unsubscribe() })
  return { tasks, latestTaskId, details, fragments, connectionState, error, reconnect, refreshTask }
}
