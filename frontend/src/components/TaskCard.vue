<script setup lang="ts">
import UiButton from './ui/UiButton.vue'
import { computed, onScopeDispose, ref, watch } from 'vue'
import type { Schema } from '../types/api'
import { getWork } from '../api/works'
import AppDrawer from './AppDrawer.vue'
import AppDialog from './AppDialog.vue'
import ResultViewer from './ResultViewer.vue'
import { session } from '../features/auth/session'
import TaskDetailsContent from './TaskDetailsContent.vue'
import TextWarnings from './TextWarnings.vue'
import VideoTaskPanel from '../features/workspace/VideoTaskPanel.vue'
import { mediaStageLabel, taskMedia } from '../types/media'
import { ApiError, createIntent, type Intent } from '../api/client'
import { releaseFailedTask, retryFailedTask } from '../api/tasks'
const props = defineProps<{ detail: Schema<'TaskDetail'>; agent?: Schema<'AgentVersion'>; fragment?: string; readOnly?: boolean; regenerationDisabled?: boolean; allowPlanRevision?: boolean; quickGeneration?: boolean; compactLabel?: string }>()
const emit = defineEmits<{ regenerate: [work: Schema<'WorkDetail'>]; mediaChanged: [taskId?: string] }>()
const media = computed(() => taskMedia(props.detail))
const liveMedia = computed(() => !['SUCCEEDED', 'FAILED', 'MANUALLY_CLOSED', 'SAVING', 'SAVE_RECOVERY'].includes(props.detail.task.state) ? media.value : null)
const displayState = computed(() => liveMedia.value ? mediaStageLabel(liveMedia.value) : states[props.detail.task.state])
const expanded = ref(false), works = ref<Schema<'WorkDetail'>[]>([]), error = ref(''), loadingWorks = ref(false)
const warnings = computed(() => [...new Set(works.value.flatMap(work => work.warnings || []))])
const states: Record<string, string> = { SUBMITTED: '已受理', QUEUED: '排队中', SUBMITTING: '提交中', RUNNING: '生成中', INVESTIGATING: '待核查，尚未成功', SAVING: '正在保存完整结果', SAVE_RECOVERY: '保存恢复中，尚未成功', SUCCEEDED: '生成成功', FAILED: '生成失败', MANUALLY_CLOSED: '人工关闭' }
const taskName = computed(() => props.agent?.kind === 'image' ? '图片创作' : props.agent?.kind === 'video' ? '视频创作' : props.agent?.kind === 'copy' ? '文案创作' : props.agent?.name || '创作任务')
const regenerationHint = computed(() => {
  const remaining = props.detail.regeneration?.free_regenerations_remaining
  if (props.quickGeneration || props.readOnly || props.detail.task.state !== 'SUCCEEDED' || remaining === undefined) return ''
  return remaining > 0 ? `免费重新生成剩余 ${remaining} 次` : '免费次数已用完，再次生成将计费'
})
const taskNote = computed(() => ({ SUBMITTED: '任务已受理，正在准备生成。', QUEUED: '任务正在排队，可稍后返回查看。', SUBMITTING: '正在确认受理状态，请等待原任务更新。', RUNNING: '任务正在执行，可离开此页面稍后查看。', INVESTIGATING: '正在核查受理状态，积分保持冻结。', SAVING: '正在保存完整成果，积分保持冻结。', SAVE_RECOVERY: '正在等待恢复原结果保存，积分保持冻结。', SUCCEEDED: '', FAILED: '生成失败', MANUALLY_CLOSED: '任务已人工关闭，请查看详情与积分结算记录。' }[props.detail.task.state]))
const settlement: Record<string, string> = { FROZEN: '已冻结，尚未扣除', CONSUMED: '已消费', RELEASED: '已释放' }
type FailureAction = 'retry' | 'release'
const failureAction = ref<FailureAction>('retry'), confirmationOpen = ref(false), actionBusy = ref(false), actionError = ref('')
const pendingAction = ref<{ kind: FailureAction; intent: Intent<Record<string, never>> } | null>(null)
const completedAction = ref(false)
const canChooseFailure = computed(() => !props.readOnly && props.detail.task.state === 'FAILED' && props.detail.task.settlement_state === 'FROZEN')
const canRetryStoppedImage = computed(() => !props.readOnly && props.detail.task.state === 'INVESTIGATING' && props.detail.task.settlement_state === 'FROZEN' && props.detail.task.investigation_reason === 'UPSTREAM_NEEDS_INPUT' && media.value?.kind === 'image' && media.value.status === 'completed' && media.value.core_status === 'needs_input')
const canRetry = computed(() => canChooseFailure.value || canRetryStoppedImage.value)
function formatTime(value?: string) {
  if (!value || Number.isNaN(Date.parse(value))) return ''
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value))
}
function chooseFailure(kind: FailureAction) {
  if (!(kind === 'retry' ? canRetry.value : canChooseFailure.value) || actionBusy.value || pendingAction.value || completedAction.value) return
  failureAction.value = kind; actionError.value = ''; confirmationOpen.value = true
}
async function sendFailureAction() {
  if (!active() || props.readOnly || actionBusy.value) return
  if (!pendingAction.value) {
    if (!(failureAction.value === 'retry' ? canRetry.value : canChooseFailure.value)) return
    pendingAction.value = { kind: failureAction.value, intent: createIntent({}) }
  }
  const command = pendingAction.value, taskId = props.detail.task.task_id
  actionBusy.value = true; actionError.value = ''
  try {
    const result = command.kind === 'retry' ? await retryFailedTask(taskId, command.intent) : await releaseFailedTask(taskId, command.intent)
    if (!result || (command.kind === 'retry' ? !('task' in result && result.task.task_id) : !('settlement_state' in result && result.settlement_state === 'RELEASED'))) throw new Error('Unconfirmed action')
    if (!active() || taskId !== props.detail.task.task_id) return
    pendingAction.value = null; confirmationOpen.value = false; completedAction.value = true; emit('mediaChanged', command.kind === 'retry' && 'task' in result ? result.task.task_id : undefined)
  } catch (cause) {
    if (!active() || taskId !== props.detail.task.task_id) return
    if (cause instanceof ApiError && cause.status >= 400 && cause.status < 500) {
      pendingAction.value = null; confirmationOpen.value = false
      actionError.value = cause.code === 'QUOTE_STALE' ? '原报价已变更，积分仍保持冻结。请释放积分后按新报价重新创作。' : canRetryStoppedImage.value && cause.status === 409 ? '暂未确认原任务可安全重试，已保留任务和冻结积分。请刷新进度后再试。' : cause.message
      emit('mediaChanged')
    } else actionError.value = '操作结果尚未确认，请重试原操作核对结果。'
  } finally { if (active() && taskId === props.detail.task.task_id) actionBusy.value = false }
}
let revision = 0, alive = true
const epoch = session.epoch.value
const active = () => alive && epoch === session.epoch.value
onScopeDispose(() => { alive = false; revision++ })
async function loadWorks() {
  if (!active()) return
  const stamp = ++revision
  const ids = [...props.detail.task.work_ids]
  error.value = ''; loadingWorks.value = true
  try {
    const values = await Promise.all(ids.map(id => getWork(id)))
    if (active() && stamp === revision) works.value = values
  } catch {
    if (active() && stamp === revision) error.value = '作品暂时无法读取，请重试或在作品页核对。'
  } finally {
    if (active() && stamp === revision) loadingWorks.value = false
  }
}
watch(() => [props.detail.task.task_id, props.detail.task.work_ids.join(',')].join(':'), () => { works.value = []; void loadWorks() }, { immediate: true })
</script>
<template>
  <article class="task-output" :class="{ 'quick-original-task': !!compactLabel }" :data-task-id="detail.task.task_id">
    <div class="task-card" :class="{ 'task-failed': detail.task.state === 'FAILED' }">
      <div class="task-heading">
        <span v-if="!compactLabel" class="task-kind-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path v-if="agent?.kind === 'image'" d="M4 4h16v16H4z M4 16l5-5 4 4 3-3 4 4 M8 8h.01"/><path v-else-if="agent?.kind === 'video'" d="M4 5h16v14H4z M10 9l5 3-5 3z"/><path v-else d="M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6 M9 16h6"/></svg></span>
        <div class="task-title"><h3>{{ compactLabel || taskName }}</h3><small v-if="!compactLabel">任务 {{ detail.task.display_number || '编号待更新' }}</small></div>
        <span class="status-label" :class="{ 'status-warning': ['INVESTIGATING', 'SAVE_RECOVERY'].includes(detail.task.state), 'status-error': detail.task.state === 'FAILED' }">{{ displayState }}</span>
        <UiButton class="button details-button" type="button" @click="expanded = true">任务详情<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg></UiButton>
      </div>
      <template v-if="!compactLabel || detail.task.state !== 'SUCCEEDED'"><p v-if="taskNote && !liveMedia" class="task-state-note">{{ canChooseFailure ? '生成失败，积分保持冻结。你可以重试，或释放积分返还可用余额。' : taskNote }}</p>
      <p v-if="canRetryStoppedImage" class="task-state-note">图片任务已停止，等待补充资料。可使用原资料重试；系统将先核验原任务，确认未开始图片生成后再提交。</p>
      <div v-if="canRetry && !completedAction" class="failed-task-actions"><UiButton class="button primary" type="button" data-failed-retry :disabled="actionBusy || !!pendingAction" @click="chooseFailure('retry')">重试</UiButton><UiButton v-if="canChooseFailure" class="button" type="button" data-failed-release :disabled="actionBusy || !!pendingAction" @click="chooseFailure('release')">释放积分</UiButton></div>
      <p v-if="actionError" class="field-error" role="alert">{{ actionError }}</p>
      <UiButton v-if="pendingAction && !readOnly" class="button" type="button" data-repeat-failed-action :disabled="actionBusy" @click="sendFailureAction">{{ actionBusy ? '正在处理…' : '重试原操作' }}</UiButton>
      <VideoTaskPanel v-if="liveMedia?.kind === 'video' && !readOnly" :task-id="detail.task.task_id" :media="liveMedia" :allow-plan-revision="allowPlanRevision" @changed="$emit('mediaChanged')" />
      <p v-if="detail.task.state !== 'FAILED' && detail.task.investigation_reason && !canRetryStoppedImage" class="task-state-note">{{ detail.task.investigation_reason }}</p>
      <div v-if="fragment && agent?.kind === 'copy'" class="transient"><small>临时文案片段，尚未形成完整作品</small><p>{{ fragment }}</p></div>
      <section v-for="(work, workIndex) in works" :key="work.work_id" class="work-output"><h4 v-if="works.length > 1" class="work-label">产物 {{ workIndex + 1 }}</h4><ResultViewer :work="work" document-layout :show-labels="work.items.length > 1 && !(quickGeneration && work.kind === 'image')" :class="{ 'image-gallery': work.kind === 'image' && work.items.length > 1 }"><template #actions><UiButton v-if="!readOnly" class="button regenerate-action" type="button" :disabled="regenerationDisabled" @click="$emit('regenerate', work)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 7v5h-5 M4 17v-5h5 M6 7a7 7 0 0 1 12-1l2 6 M18 17a7 7 0 0 1-12 1l-2-6"/></svg>重新生成</UiButton></template></ResultViewer></section>
      <p v-if="regenerationHint && works.length" class="regeneration-hint">{{ regenerationHint }}</p>
      <div v-if="error || loadingWorks" class="result-read-state"><p v-if="loadingWorks" role="status">正在读取产物…</p><template v-else><p role="alert">{{ error }}</p><UiButton class="button" type="button" data-work-retry @click="loadWorks">重新读取作品</UiButton></template></div>
      <p v-if="detail.task.state === 'SUCCEEDED' && !detail.task.work_ids.length" class="task-state-note">作品当前不可展示，任务与积分记录仍保留。</p>
      <div class="task-footer"><span>本次费用 {{ detail.task.quote.credits }} 积分 · {{ settlement[detail.task.settlement_state] }}</span><time v-if="detail.task.created_at" :datetime="detail.task.created_at">生成时间 {{ formatTime(detail.task.created_at) }}</time></div></template>
    </div>
    <AppDrawer v-model:open="expanded" title="任务详情">
      <template v-if="compactLabel"><ResultViewer v-for="work in works" :key="work.work_id" :work="work" document-layout /><p v-if="loadingWorks" role="status">正在读取产物…</p><template v-if="error"><p role="alert">{{ error }}</p><UiButton class="button" type="button" data-work-retry @click="loadWorks">重新读取作品</UiButton></template></template><TextWarnings :warnings="warnings" />
      <TaskDetailsContent :detail="detail" :agent="agent" :state-label="displayState" :settlement-label="settlement[detail.task.settlement_state] || detail.task.settlement_state" :created-at="formatTime(detail.task.created_at)" />
    </AppDrawer>
    <AppDialog :open="confirmationOpen && !readOnly" @update:open="confirmationOpen = $event" :title="failureAction === 'retry' ? '确认重试' : '确认释放积分'" :purpose="failureAction === 'retry' ? 'charge' : 'edit'">
      <p v-if="canRetryStoppedImage">先核验原图片任务已停止且未开始图片生成，再使用原资料重新创作；如仍缺少必要资料，重试也可能再次停止。</p>
      <p v-if="failureAction === 'retry'">使用本任务的原始商品资料和指令重新创作。已冻结的 {{ detail.task.quote.credits }} 积分将用于本次重试，完整成果保存后消费；原报价失效时不提交。</p><p v-else>将本任务冻结的 {{ detail.task.quote.credits }} 积分返还可用余额。释放后，此任务不能再使用冻结额度重试。</p>
      <p v-if="actionError" class="field-error" role="alert">{{ actionError }}</p>
      <template #actions><UiButton class="button primary" type="button" data-confirm-failed-action :disabled="actionBusy || !!pendingAction" @click="sendFailureAction">{{ actionBusy ? '正在处理…' : failureAction === 'retry' ? '确认重试' : '确认释放积分' }}</UiButton></template>
    </AppDialog>
  </article>
</template>
<style scoped>
.task-output { margin-top:16px; padding:0; border:0; background:transparent; min-width:0 }
.task-output:first-child { margin-top:0 }
.task-card { padding:0; margin:0; border:0; background:transparent; border-radius:0; min-width:0 }
.task-heading { display:flex; align-items:center; flex-wrap:wrap; gap:8px }
.task-kind-icon { display:grid; place-items:center; width:32px; height:32px; flex-shrink:0; border-radius:8px; background:var(--color-background); color:var(--color-primary) }
.task-kind-icon svg { width:18px; height:18px }
.task-title { display:flex; align-items:baseline; flex-wrap:wrap; gap:4px 10px; min-width:0; flex:1 }
.task-title h3 { font-size:15px; font-weight:600; margin:0 }
.task-title small { color:var(--color-muted); font-size:12px; font-variant-numeric:tabular-nums; overflow-wrap:anywhere }
.status-label { color:var(--color-muted); font-size:12px; line-height:1.6; padding:3px 8px; border-radius:6px; background:var(--color-background) }
.status-warning { color:var(--color-warning) }
.status-error { color:var(--color-danger) }
.task-state-note { margin:16px 0 0; color:var(--color-muted); font-size:13px; line-height:1.8 }
.task-failed .task-state-note,.result-read-state p { color:var(--color-danger) }
.task-footer { display:flex; align-items:baseline; justify-content:space-between; flex-wrap:wrap; gap:4px 16px; margin-top:18px; padding-top:12px; border-top:1px solid var(--color-border); color:var(--color-muted); font-size:12px; line-height:1.7; font-variant-numeric:tabular-nums }
.failed-task-actions { display:flex; gap:8px; margin:12px 0 }
.details-button { border:0; background:transparent; color:var(--color-muted); padding:4px 0 4px 6px; font-size:12px; flex-shrink:0 }
.details-button svg { width:14px; height:14px }
.result-read-state { margin-top:16px; font-size:13px }
.regeneration-hint { margin:8px 0 0; color:var(--color-muted); font-size:12px; line-height:1.6 }
.transient { margin-top:16px; padding:16px; background:var(--color-background); border-radius:8px }
.transient small { color:var(--color-muted); font-size:12px }
.transient p { margin:8px 0 0; white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.9 }
.work-output { margin-top:20px; min-width:0 }
.work-output+.work-output { margin-top:24px; padding-top:20px; border-top:1px solid var(--color-border) }
.work-label { margin:0 0 12px; font-size:13px; font-weight:600; color:var(--color-muted) }
.task-card :deep(.result-item) { margin-top:0; min-width:0 }
.task-card :deep(.result-item+.result-item) { margin-top:24px; padding-top:20px; border-top:1px solid var(--color-border) }
.task-card :deep(.image-gallery .result-item+.result-item) { margin-top:0; padding-top:0; border-top:0 }
.task-card :deep(.image-gallery) { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(200px,100%),1fr)); align-items:start; gap:16px }
.task-card :deep(.image-gallery .result-item>img) { display:block; width:100%; max-height:560px; background:var(--color-background) }
.task-card :deep(.image-gallery .result-actions) { flex-wrap:wrap }
.task-card :deep(.copy-result) { margin:0; padding:0; line-height:1.95; border:0; border-radius:0; background:transparent; color:var(--color-text) }
.task-card :deep(.result-actions) { border:0; padding-top:0; margin-top:12px; gap:6px }
@media(max-width:1180px) { .task-title { display:block } .task-title small { display:block } }
@media(max-width:700px) { .task-heading { gap:6px } .task-kind-icon { width:28px; height:28px } .status-label { order:4; margin-left:34px } .details-button { margin-left:auto } .task-footer { display:block } .task-footer time { display:block; margin-top:4px } }
</style>
