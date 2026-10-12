import { onScopeDispose, ref, shallowRef, toValue, watch, type MaybeRefOrGetter } from 'vue'
import { getConversation } from '../../api/conversations'
import { getTask, listTasks } from '../../api/tasks'
import { listWorks } from '../../api/works'
import { connectTaskEvents, type Schema } from '../../types/api'
import { onIdentityChange, session } from '../auth/session'

/** One owner per mounted conversation. Reconnects reconcile persisted originals; never submit. */
export function useTaskStream(conversationId: MaybeRefOrGetter<string>) {
  const tasks = shallowRef<Schema<'TaskView'>[]>([])
  const details = shallowRef<Record<string, Schema<'TaskDetail'>>>({})
  const fragments = ref<Record<string, string>>({})
  const connectionState = ref<'connecting' | 'open' | 'recovering' | 'closed'>('closed')
  const error = ref('')
  let source: EventSource | undefined, timer: ReturnType<typeof setTimeout> | undefined
  let cursor = '', revision = 0, disposed = false
  function close() { source?.close(); source = undefined; clearTimeout(timer); timer = undefined }
  function token() { return { revision, epoch: session.epoch.value, id: toValue(conversationId) } }
  function current(t: ReturnType<typeof token>) { return !disposed && t.revision === revision && t.epoch === session.epoch.value && t.id === toValue(conversationId) }
  function merge(detail: Schema<'TaskDetail'>) {
    if (detail.conversation_id !== toValue(conversationId)) return
    const previous = tasks.value.find(t => t.task_id === detail.task.task_id)
    if (previous && previous.state_version > detail.task.state_version) return
    details.value = { ...details.value, [detail.task.task_id]: detail }
    tasks.value = previous ? tasks.value.map(t => t.task_id === detail.task.task_id ? detail.task : t) : [...tasks.value, detail.task]
    if (['SUCCEEDED', 'FAILED', 'MANUALLY_CLOSED'].includes(detail.task.state)) delete fragments.value[detail.task.task_id]
  }
  async function refreshTask(id: string, t = token()) {
    const detail = await getTask(id)
    if (current(t)) merge(detail)
  }
  async function reconcile(t: ReturnType<typeof token>) {
    await getConversation(t.id)
    const ids: string[] = []
    let next: string | undefined
    do {
      const page = await listTasks(t.id, next)
      if (!current(t)) return
      ids.push(...page.items.map(x => x.task_id)); next = page.next_cursor ?? undefined
    } while (next)
    await Promise.all(ids.map(id => refreshTask(id, t)))
    // Works are independently durable and may have been published while disconnected.
    do {
      const page = await listWorks({ conversation_id: t.id, cursor: next })
      if (!current(t)) return
      next = page.next_cursor ?? undefined
    } while (next)
  }
  function open(t: ReturnType<typeof token>) {
    if (!current(t)) return
    const owned = connectTaskEvents(cursor || undefined); source = owned
    const live = () => current(t) && source === owned
    owned.onopen = () => { if (live()) connectionState.value = 'open' }
    owned.addEventListener('task.updated', event => {
      if (!live()) return
      const e = event as MessageEvent
      try {
        const durable = JSON.parse(e.data) as Schema<'DurableEventView'>
        if (!durable.payload?.task_id) return
        if (e.lastEventId) cursor = e.lastEventId
        const known = tasks.value.find(x => x.task_id === durable.payload.task_id)
        if (known && known.state_version >= durable.payload.state_version) return
        void refreshTask(durable.payload.task_id, t).catch(() => { if (live()) void reconnect() })
      } catch { void reconnect() }
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
      cursor = (event as MessageEvent).lastEventId
      void reconnect()
    })
    owned.onerror = () => { if (live()) void recover(2500) }
  }
  async function recover(retryDelay = 0) {
    close()
    revision++
    const t = token()
    if (!t.id || disposed) { connectionState.value = 'closed'; return }
    connectionState.value = 'recovering'; error.value = ''
    try {
      await reconcile(t)
      if (!current(t)) return
      connectionState.value = 'connecting'
      if (retryDelay) timer = setTimeout(() => open(t), retryDelay)
      else open(t)
    } catch {
      if (!current(t)) return
      error.value = '连接暂时中断，正在核对原任务。'; connectionState.value = 'recovering'
      timer = setTimeout(() => { if (current(t)) void reconnect() }, 2500)
    }
  }
  function reconnect() { return recover() }
  function clear() { revision++; close(); cursor = ''; tasks.value = []; details.value = {}; fragments.value = {}; error.value = ''; connectionState.value = 'closed' }
  const unsubscribe = onIdentityChange(clear)
  watch(() => toValue(conversationId), () => { clear(); void reconnect() }, { immediate: true, flush: 'sync' })
  onScopeDispose(() => { disposed = true; clear(); unsubscribe() })
  return { tasks, details, fragments, connectionState, error, reconnect, refreshTask }
}
