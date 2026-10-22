<script setup lang="ts">
import UiButton from '../../components/ui/UiButton.vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import { computed, nextTick, onScopeDispose, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createConversation } from '../../api/conversations'
import { deleteTask, getTask, listTasks } from '../../api/tasks'
import { createQuickRun, listQuickRuns } from '../../api/quickGeneration'
import { quickGenerationRevision } from '../quick-generation/activity'
import type { Schema } from '../../types/api'
import { session } from '../auth/session'
import AppIcon from '../../components/AppIcon.vue'
import AppDialog from '../../components/AppDialog.vue'

const route = useRoute(), router = useRouter()
const quickMode = computed(() => route.path === '/workspace/quick' || route.path.startsWith('/workspace/quick/'))
const items = ref<Schema<'TaskView'>[]>([])
const quickRuns = ref<Schema<'QuickSummary'>[]>([])
const quickStages = ['商品确认', '营销文案', '图片生成', '视频生成', '已完成']
const details = ref<Record<string, Schema<'TaskDetail'>>>({})
const error = ref(''), busy = ref(false), loading = ref(false), cursor = ref<string>()
const creationError = ref('')
const deleteTarget = ref<Schema<'TaskView'>>()
const deleteOpen = ref(false), deleting = ref(false), deleteError = ref('')
const deletedIds = ref(new Set<string>())
const navigation = ref<HTMLElement>()
const states: Record<Schema<'TaskState'>, string> = { SUBMITTED: '已受理', QUEUED: '排队中', SUBMITTING: '提交中', RUNNING: '生成中', INVESTIGATING: '待核查', SAVING: '保存中', SAVE_RECOVERY: '保存恢复中', SUCCEEDED: '生成成功', FAILED: '生成失败', MANUALLY_CLOSED: '已关闭' }
const tasks = computed(() => quickMode.value ? [] : items.value.filter(item => !deletedIds.value.has(item.task_id) && details.value[item.task_id]))
const visibleQuickRuns = computed(() => quickMode.value ? quickRuns.value : [])
const selectedId = computed(() => route.params.runId ? 'quick:' + route.params.runId : typeof route.query.task === 'string' ? route.query.task : tasks.value.find(item => details.value[item.task_id]?.conversation_id === route.params.conversationId)?.task_id || '')
const historySelection = computed(() => (quickMode.value ? visibleQuickRuns.value.some(item => 'quick:' + item.run_id === selectedId.value) : tasks.value.some(item => item.task_id === selectedId.value)) ? selectedId.value : '')
const taskTitle = (item: Schema<'TaskView'>) => String(details.value[item.task_id]?.input.product?.name || '创作任务')
const taskLink = (item: Schema<'TaskView'>) => ({ path: '/workspace/' + details.value[item.task_id]!.conversation_id, query: { task: item.task_id } })
const timeLabel = (value: string) => Number.isNaN(Date.parse(value)) ? '' : new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Shanghai' }).format(new Date(value))
let revision = 0, alive = true, hasLoadedMore = false, quickCreationId = ''
onScopeDispose(() => { alive = false; revision++ })
async function load(more = false) {
  if (more && loading.value) return
  const stamp = ++revision, epoch = session.epoch.value
  const current = () => alive && stamp === revision && epoch === session.epoch.value
  loading.value = true
  try {
    const page = await listTasks(undefined, more ? cursor.value : undefined, undefined, 'ordinary')
    if (!current()) return
    page.items = page.items.filter(item => !deletedIds.value.has(item.task_id))
    const nextDetails = { ...details.value }
    const knownTasks = new Map([...items.value, ...page.items].map(item => [item.task_id, item]))
    const missing = [...knownTasks.values()].filter(item => !nextDetails[item.task_id])
    const results = await Promise.allSettled(missing.map(item => getTask(item.task_id)))
    if (!current()) return
    for (const result of results) if (result.status === 'fulfilled') nextDetails[result.value.task.task_id] = result.value
    details.value = nextDetails
    if (more) items.value = [...items.value, ...page.items.filter(item => !items.value.some(existing => existing.task_id === item.task_id))]
    else {
      // A background refresh updates the newest page without losing already loaded history.
      const incoming = new Set(page.items.map(item => item.task_id))
      items.value = [...page.items, ...items.value.filter(item => !incoming.has(item.task_id))]
    }
    if (more || !hasLoadedMore) cursor.value = page.next_cursor ?? undefined
    if (more) hasLoadedMore = true
    error.value = results.some(result => result.status === 'rejected') ? '部分任务暂时无法读取，请重试。' : ''
  } catch { if (current()) error.value = '任务暂时无法读取，请重试。' }
  finally { if (current()) loading.value = false }
}
async function create() {
  if (busy.value) return
  creationError.value = ''
  busy.value = true
  const epoch = session.epoch.value
  const mode = quickMode.value
  try {
    if (mode) {
      quickCreationId ||= crypto.randomUUID()
      const item = await createQuickRun(quickCreationId)
      if (alive && epoch === session.epoch.value && quickMode.value) {
        await router.push('/workspace/quick/' + item.run_id)
        if (route.path === '/workspace/quick/' + item.run_id) quickCreationId = ''
      }
      return
    }
    const item = await createConversation({ title: '新任务' })
    if (alive && epoch === session.epoch.value && !quickMode.value) await router.push('/workspace/' + item.conversation_id)
  } catch { if (alive && epoch === session.epoch.value) creationError.value = mode ? '快速生成创建失败，请重试。' : '新任务创建失败，请重试。' }
  finally { busy.value = false }
}
function selectTask(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (value.startsWith('quick:')) { void router.push('/workspace/quick/' + value.slice(6)); return }
  const item = tasks.value.find(task => task.task_id === value)
  if (item) void router.push(taskLink(item))
}
function confirmDelete(item: Schema<'TaskView'>) {
  deleteTarget.value = item; deleteError.value = ''; deleteOpen.value = true
}
async function remove() {
  const item = deleteTarget.value
  if (!item || deleting.value) return
  const epoch = session.epoch.value, path = route.fullPath
  const wasSelected = selectedId.value === item.task_id
  deleting.value = true; deleteError.value = ''
  try {
    await deleteTask(item.task_id)
    if (!alive || epoch !== session.epoch.value) return
    deletedIds.value.add(item.task_id)
    items.value = items.value.filter(task => task.task_id !== item.task_id)
    revision++; loading.value = false
    deleteOpen.value = false
    if (wasSelected && route.fullPath === path) {
      const next = tasks.value[0]
      if (next) await router.replace(taskLink(next))
      else await router.replace('/workspace/ordinary')
    }
    await nextTick()
    if (alive && epoch === session.epoch.value) navigation.value?.querySelector<HTMLElement>('[aria-current="page"], .primary')?.focus()
  } catch { if (alive && epoch === session.epoch.value) deleteError.value = '任务删除失败，请重试。' }
  finally { if (alive && epoch === session.epoch.value) deleting.value = false }
}
watch(session.epoch, () => {
  revision++; items.value = []; details.value = {}; cursor.value = undefined; hasLoadedMore = false; loading.value = false; error.value = ''; creationError.value = ''
  quickRuns.value = []; quickCreationId = ''; quickRevision++; quickLoading.value = false; quickError.value = ''
  deletedIds.value.clear(); deleteOpen.value = false; deleteTarget.value = undefined; deleting.value = false; deleteError.value = ''
}, { flush: 'sync' })
watch(quickMode, () => { creationError.value = ''; revision++; loading.value = false })
watch([() => route.fullPath, () => session.account.value, () => session.epoch.value], () => { if (!route.meta.public && !quickMode.value) void load() }, { immediate: true })
let quickRevision = 0
const quickLoading = ref(false), quickError = ref('')
async function loadQuick() {
  const stamp = ++quickRevision, epoch = session.epoch.value
  quickLoading.value = true; quickError.value = ''
  try { const value = await listQuickRuns(); if (alive && stamp === quickRevision && epoch === session.epoch.value && Array.isArray(value)) quickRuns.value = value }
  catch { if (alive && stamp === quickRevision && epoch === session.epoch.value) quickError.value = '快速生成记录暂时无法读取，请重试。' }
  finally { if (alive && stamp === quickRevision && epoch === session.epoch.value) quickLoading.value = false }
}
watch([() => route.fullPath, () => session.account.value, () => session.epoch.value, () => quickGenerationRevision.value], () => {
  if (!route.meta.public && quickMode.value) void loadQuick()
}, { immediate: true })
const historyLoading = computed(() => quickMode.value ? quickLoading.value : loading.value)
const historyError = computed(() => quickMode.value ? quickError.value : error.value)
const historyCount = computed(() => tasks.value.length + visibleQuickRuns.value.length)
const retryHistory = () => quickMode.value ? loadQuick() : load()
</script>
<template>
  <div ref="navigation" class="conversation-nav task-nav">
    <nav class="workspace-mode-switch" aria-label="工作台模式">
      <RouterLink to="/workspace/quick" :class="{ 'is-active': quickMode }" :aria-current="quickMode ? 'page' : undefined">快速生成</RouterLink>
      <RouterLink to="/workspace/ordinary" :class="{ 'is-active': !quickMode }" :aria-current="!quickMode ? 'page' : undefined">专业工作台</RouterLink>
    </nav>
    <UiButton class="button primary new-task-button" type="button" :disabled="busy" :aria-busy="busy" @click="create"><AppIcon name="create" />{{ busy ? '创建中…' : quickMode ? '新建快速生成' : '新建任务' }}</UiButton>
    <p v-if="creationError" class="creation-error" role="alert">{{ creationError }}</p>
    <label class="mobile-history" for="task-choice">最近任务</label>
    <UiSelect id="task-choice" class="mobile-history" placeholder="选择最近任务" :value="historySelection" @change="selectTask">
      <option value="">选择最近任务</option>
      <option v-for="item in visibleQuickRuns" :key="'quick:' + item.run_id" :value="'quick:' + item.run_id">{{ item.title }} · 快速生成 · {{ quickStages[item.step - 1] }}</option>
      <option v-for="item in tasks" :key="item.task_id" :value="item.task_id">{{ taskTitle(item) }} · {{ timeLabel(item.created_at) }} · {{ states[item.state] }}</option>
    </UiSelect>
    <UiButton v-if="tasks.some(item => item.task_id === selectedId)" class="button danger mobile-history mobile-task-delete" type="button" @click="confirmDelete(tasks.find(item => item.task_id === selectedId)!)">删除所选任务</UiButton>
    <nav class="desktop-history" aria-label="最近任务">
      <p class="history-heading">最近任务<span v-if="historyCount">{{ historyCount }}</span></p>
      <RouterLink v-for="item in visibleQuickRuns" :key="'quick:' + item.run_id" class="task-history-item quick-history-item" :class="{ 'is-selected': selectedId === 'quick:' + item.run_id }" :to="'/workspace/quick/' + item.run_id" :aria-current="selectedId === 'quick:' + item.run_id ? 'page' : undefined"><span class="task-list-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5"/></svg></span><span class="task-title" :title="item.title">{{ item.title }}</span><span class="task-meta">快速生成 · {{ quickStages[item.step - 1] }}</span></RouterLink>
      <div v-for="item in tasks" :key="item.task_id" class="task-history-row">
      <RouterLink v-slot="{ href, navigate }" :to="taskLink(item)" custom>
        <a class="task-history-item" :class="{ 'is-selected': selectedId === item.task_id }" :href="href" :aria-current="selectedId === item.task_id ? 'page' : undefined" @click="navigate">
          <span class="task-list-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6 M9 16h6" /></svg></span>
          <span class="task-title" :title="taskTitle(item)">{{ taskTitle(item) }}</span>
          <span class="task-meta"><span class="task-state" :class="{ 'is-running': ['SUBMITTED','QUEUED','SUBMITTING','RUNNING','SAVING'].includes(item.state), 'is-warning': ['INVESTIGATING','SAVE_RECOVERY'].includes(item.state), 'is-failed': item.state === 'FAILED' }">{{ states[item.state] }}</span><time :datetime="item.created_at" :title="item.created_at">{{ timeLabel(item.created_at) }}</time></span>
        </a>
      </RouterLink>
      <UiButton class="task-delete icon-button" type="button" :aria-label="'删除任务：' + taskTitle(item)" title="删除任务" @click="confirmDelete(item)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7" /></svg></UiButton>
      </div>
      <div v-if="historyLoading && !historyCount" class="history-loading" aria-label="正在读取任务"><span/><span/><span/></div>
      <p v-else-if="!historyCount && !historyError" class="history-empty">还没有创作任务</p>
      <UiButton v-if="!quickMode && cursor" class="button history-more" type="button" :disabled="loading" @click="load(true)">更多任务</UiButton>
      <div v-if="historyError" class="history-error"><p role="alert">{{ historyError }}</p><UiButton class="button" type="button" :disabled="historyLoading" @click="retryHistory">重试</UiButton></div>
    </nav>
    <UiButton v-if="!quickMode && cursor" class="button mobile-history" type="button" :disabled="loading" @click="load(true)">更多任务</UiButton>
    <div v-if="historyError" class="mobile-history history-error"><p role="alert">{{ historyError }}</p><UiButton class="button" type="button" :disabled="historyLoading" @click="retryHistory">重试</UiButton></div>
    <AppDialog v-model:open="deleteOpen" title="删除任务" purpose="delete"><template v-if="deleteTarget"><p>确认从最近任务中删除「{{ taskTitle(deleteTarget) }}」吗？</p><p>创建时间：{{ timeLabel(deleteTarget.created_at) }}</p><p>已有作品、积分和审计记录保留。进行中的任务会继续执行并正常结算。</p></template><p v-if="deleteError" class="field-error" role="alert">{{ deleteError }}</p><template #actions><UiButton class="button danger" type="button" :disabled="deleting" @click="remove">{{ deleting ? '正在删除…' : '确认删除' }}</UiButton></template></AppDialog>
  </div>
</template>

<style scoped>
.conversation-nav>.primary { min-height:44px; font-weight:600 }
.workspace-mode-switch { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); flex-shrink:0; gap:4px; padding:4px; border:1px solid var(--color-border); border-radius:10px; background:var(--color-background) }
.workspace-mode-switch>a { display:flex; align-items:center; justify-content:center; min-height:44px; padding:6px 4px; border-radius:6px; text-decoration:none; color:var(--color-muted); font-size:13px; font-weight:600 }
.workspace-mode-switch>a.is-active { background:var(--color-panel); color:var(--color-primary); box-shadow:0 1px 3px color-mix(in srgb,var(--color-text) 8%,transparent) }
.workspace-mode-switch>a:hover { color:var(--color-primary) }
.new-task-button { margin-top:12px }
@media(min-width:901px) and (pointer:fine) { .workspace-mode-switch>a { min-height:32px } }
.creation-error { grid-column:1/-1; margin:8px 0; font-size:12px; line-height:1.8; color:var(--color-danger) }
.desktop-history>.history-heading { display:flex; align-items:center; justify-content:space-between; margin:20px 0 10px; padding-inline:4px; font-size:12px; font-weight:600; color:var(--color-muted); letter-spacing:.04em }
.history-heading>span { font-size:12px; font-variant-numeric:tabular-nums; font-weight:400 }
.desktop-history .task-history-item { position:relative; display:block; padding:12px 10px; margin:4px 0; border:1px solid transparent; border-radius:10px; color:var(--color-text); text-decoration:none }
.task-history-row { position:relative }
.task-history-row .task-title { padding-right:28px }
.task-delete.icon-button { position:absolute; right:4px; top:5px; width:44px; min-height:44px; border-color:transparent; background:transparent; color:var(--color-muted) }
.task-delete:hover { color:var(--color-danger); background:var(--color-panel) }
.task-delete svg { width:16px; height:16px }
.mobile-task-delete { grid-column:1/-1; justify-self:end }
@media(min-width:901px) and (pointer:fine) { .task-delete.icon-button { width:28px; min-height:28px; height:28px; padding:5px; right:4px; top:5px } }
@media(pointer:coarse) { .task-history-row .task-title { padding-right:40px } }
.task-title { display:block; font-size:13px; font-weight:600; line-height:1.6; overflow-wrap:anywhere }
.task-meta { display:flex; align-items:center; flex-wrap:wrap; justify-content:space-between; gap:4px; margin-top:8px; color:var(--color-muted); font-size:12px; line-height:1.5 }
.task-meta time { font-size:12px; font-variant-numeric:tabular-nums }
.task-state { display:inline-flex; align-items:center; gap:5px }
.task-state::before { content:''; width:5px; height:5px; border-radius:50%; background:currentColor; opacity:.5 }
.task-state.is-running { color:var(--color-primary) }
.task-state.is-warning { color:var(--color-warning, #8b5d31) }
.desktop-history .task-history-item.is-selected { background:var(--color-panel); border-color:var(--color-border); box-shadow:0 1px 3px color-mix(in srgb,var(--color-text) 4%,transparent) }
.task-history-item.is-selected .task-title { color:var(--color-primary) }
.task-history-item.is-selected::before { content:''; position:absolute; left:-1px; top:16px; bottom:16px; width:3px; border-radius:0 3px 3px 0; background:var(--color-primary) }
.desktop-history .task-history-item:hover { background:var(--color-selected) }
.history-empty,.history-error { font-size:12px; line-height:1.8; color:var(--color-muted) }
.history-empty { padding:12px 4px }
.history-more { width:100%; margin-top:8px }
.history-error { margin-block:8px }
.history-error p { margin-bottom:8px }
.history-loading { display:grid; gap:10px; padding:10px 4px }
.history-loading>span { height:65px; border-radius:8px; background:color-mix(in srgb,var(--color-border) 50%,transparent) }
@media(min-width:901px) and (pointer:fine) { .conversation-nav>.primary { min-height:36px; font-size:13px; padding:6px 12px } }
@media(prefers-reduced-motion:no-preference) { .task-history-item { transition:background-color 160ms,border-color 160ms } }
@media(max-width:700px) { .conversation-nav>.primary { grid-column:1; grid-row:1 } .conversation-nav>label { grid-column:2; grid-row:1; text-align:right; font-size:13px } .history-error { grid-column:1/-1; margin-top:0 } }
@media(max-width:700px) { .workspace-mode-switch,.conversation-nav>.new-task-button { grid-column:1 / -1 } .workspace-mode-switch { grid-row:1 } .conversation-nav>.new-task-button { grid-row:2; margin-top:0 } .conversation-nav>label.mobile-history { grid-row:auto; grid-column:1 / -1; text-align:left } }
</style>
