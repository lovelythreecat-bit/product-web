<script setup lang="ts">
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import { computed, onScopeDispose, ref, watch } from 'vue'
import AppDrawer from '../../components/AppDrawer.vue'
import AppDialog from '../../components/AppDialog.vue'
import { ApiError, createIntent, type Intent } from '../../api/client'
import { confirmVideoPlan, supplementVideoInputs, reviseVideoPlan, getTask } from '../../api/tasks'
import { session } from '../auth/session'
import { mediaStageLabel, taskMedia, type MediaTaskState, type VideoPlanView, type VideoPlanRevision, type VideoShot } from '../../types/media'
const props = defineProps<{ taskId: string; media: MediaTaskState | null; allowPlanRevision?: boolean }>()
const emit = defineEmits<{ changed: [] }>()
type Command = { kind: 'confirm'; intent: Intent<{ plan_version: number }> } | { kind: 'inputs'; intent: Intent<{ text: string }> } | { kind: 'revise'; intent: Intent<VideoPlanRevision> }
const pending = ref<Command | null>(null), busy = ref(false), error = ref('')
const storageBlocked = ref(false)
const planOpen = ref(false), inputOpen = ref(false), confirmationOpen = ref(false)
const viewedPlan = ref<VideoPlanView | null>(null), text = ref('')
const editOpen = ref(false), replanOpen = ref(false), replanText = ref('')
const editShots = ref<VideoShot[]>([]), editMusic = ref('')
const waitingVersion = ref<number | null>(null), readingPlan = ref(false)
const confirmAfterSave = ref(false), confirmationFromEditor = ref(false)
const editBaseline = ref('')
const savedPlan = ref<VideoPlanView | null>(null)
const editDirty = computed(() => JSON.stringify([editShots.value, editMusic.value]) !== editBaseline.value)
const editableShotLabels = { content: '画面', action: '动作', shot_size: '景别', camera: '运镜', subtitle_text: '字幕', voiceover_text: '旁白' } as const
const stage = computed(() => mediaStageLabel(props.media))
const questions = computed(() => Array.isArray(props.media?.questions) ? props.media.questions.filter(q => typeof q === 'string') : [])
const storageKey = computed(() => 'video-command-v1:' + (session.profile.value?.user_id || 'anonymous') + ':' + props.taskId)
const visualLabels: Record<string, string> = { product_reference: '商品参考', scene: '场景', lighting: '光线', palette: '配色', style: '风格', character: '人物', scene_change: '场景衔接' }
const shotLabels: Record<string, string> = { content: '画面', action: '动作', shot_size: '景别', camera: '运镜', start_frame: '起始帧', end_frame: '结束帧', subtitle_text: '字幕', voiceover_text: '旁白' }
const hasDisplayValue = (value: unknown) => typeof value === 'number' || typeof value === 'string' && value.length > 0
let alive = true, revision = 0
onScopeDispose(() => { alive = false; revision++ })
watch(() => [props.taskId, session.epoch.value], () => {
  revision++; busy.value = false; storageBlocked.value = false; pending.value = null; error.value = ''; planOpen.value = false; inputOpen.value = false; confirmationOpen.value = false; editOpen.value = false; replanOpen.value = false; waitingVersion.value = null; confirmAfterSave.value = false; confirmationFromEditor.value = false; readingPlan.value = false; savedPlan.value = null
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey.value) || 'null')
    if (saved && ['confirm', 'inputs', 'revise'].includes(saved.kind) && typeof saved.intent?.key === 'string' && typeof saved.intent?.body === 'string') {
      const body = JSON.parse(saved.intent.body)
      // This legacy payload exceeds the server schema and could never have
      // reached a command handler. Keep its text editable without replaying it.
      if (saved.kind === 'inputs' && typeof body.text === 'string' && Array.from(body.text).length > 10000) {
        text.value = body.text; sessionStorage.removeItem(storageKey.value)
        error.value = '补充资料最多 10000 字，请修改后提交。'; return
      }
      if (saved.kind === 'confirm' && Number.isInteger(body.plan_version) && body.plan_version > 0 || saved.kind === 'inputs' && typeof body.text === 'string' && body.text.trim() || saved.kind === 'revise' && Number.isInteger(body.plan_version) && body.plan_version > 0 && (typeof body.instruction === 'string' && body.instruction.trim() || body.patch && typeof body.patch === 'object')) pending.value = saved
      else throw new Error('Invalid saved video intent')
    }
    else if (saved !== null) throw new Error('Invalid saved video command')
  } catch { storageBlocked.value = true; error.value = '原操作记录无法读取，请刷新原任务核对状态；暂不能提交新的操作。' }
}, { immediate: true })
function viewPlan() {
  if (waitingVersion.value !== null || readingPlan.value) { error.value = '正在读取已保存的新方案，请稍后再试。'; return }
  const plan = props.allowPlanRevision && savedPlan.value && savedPlan.value.plan_version > (props.media?.plan?.plan_version || 0) ? savedPlan.value : props.media?.plan
  if (!plan || !Number.isInteger(plan.plan_version) || !plan.document || typeof plan.document !== 'object') { error.value = '方案尚未完整读取，请刷新原任务。'; return }
  viewedPlan.value = JSON.parse(JSON.stringify(plan)); planOpen.value = true; error.value = ''
}
function askConfirmation() { if (!viewedPlan.value || pending.value || waitingVersion.value !== null || readingPlan.value) return; confirmationFromEditor.value = false; planOpen.value = false; confirmationOpen.value = true }
function loadEditor() {
  editShots.value = JSON.parse(JSON.stringify(viewedPlan.value?.document.shots || []))
  editMusic.value = viewedPlan.value?.document.music_direction || ''
  editBaseline.value = JSON.stringify([editShots.value, editMusic.value])
}
function acceptSavedPlan(media: MediaTaskState | null) {
  if (waitingVersion.value === null || !media?.plan || !Number.isInteger(media.plan.plan_version) || !media.plan.document || typeof media.plan.document !== 'object' || media.status !== 'awaiting_confirmation' || media.plan.plan_version !== media.head_plan_version || media.plan.plan_version <= waitingVersion.value) return false
  savedPlan.value = JSON.parse(JSON.stringify(media.plan)); viewedPlan.value = JSON.parse(JSON.stringify(media.plan)); waitingVersion.value = null; error.value = ''; loadEditor()
  if (confirmAfterSave.value && editOpen.value) { confirmationFromEditor.value = true; editOpen.value = false; confirmationOpen.value = true }
  confirmAfterSave.value = false
  return true
}
watch(() => props.media, media => { acceptSavedPlan(media) }, { deep: true })
async function readSavedPlan() {
  if (readingPlan.value || waitingVersion.value === null) return
  const stamp = revision, taskId = props.taskId
  readingPlan.value = true
  try { const detail = await getTask(taskId); if (alive && stamp === revision) acceptSavedPlan(taskMedia(detail)) }
  catch { if (alive && stamp === revision) error.value = '新方案暂时无法读取，请重新读取；不会确认旧版本。' }
  finally { if (alive && stamp === revision) readingPlan.value = false }
}
function closeEditor(open: boolean) {
  if (busy.value || readingPlan.value) return
  editOpen.value = open
  if (!open) confirmAfterSave.value = false
}
function closeConfirmation(open: boolean) {
  if (busy.value) return
  confirmationOpen.value = open
  if (!open && confirmationFromEditor.value && !pending.value) editOpen.value = true
}
function confirmEditedPlan() {
  if (!props.allowPlanRevision || busy.value || pending.value || readingPlan.value || waitingVersion.value !== null) return
  if (editDirty.value) { confirmAfterSave.value = true; sendRevision(true); return }
  confirmationFromEditor.value = true; editOpen.value = false; confirmationOpen.value = true
}
function openRevision(edit: boolean) {
  if (!props.allowPlanRevision || props.media?.status !== 'awaiting_confirmation' || pending.value || busy.value || waitingVersion.value !== null || readingPlan.value) return
  viewPlan()
  if (!viewedPlan.value || !planOpen.value) return
  planOpen.value = false
  if (edit) {
    loadEditor(); editOpen.value = true
  } else { replanText.value = ''; replanOpen.value = true }
}
function sendRevision(edit: boolean) {
  if (!props.allowPlanRevision || !viewedPlan.value || props.media?.status !== 'awaiting_confirmation' || pending.value || busy.value || waitingVersion.value !== null || readingPlan.value) return
  const body: VideoPlanRevision = { plan_version: viewedPlan.value.plan_version }
  if (edit) {
    const shot_texts = editShots.value.filter(shot => shot.shot_id).map(shot => Object.fromEntries(Object.entries(shot).filter(([key]) => key === 'shot_id' || key in editableShotLabels))) as NonNullable<VideoPlanRevision['patch']>['shot_texts']
    if (!shot_texts?.length && editMusic.value === (viewedPlan.value.document.music_direction || '')) { error.value = '当前方案暂无可编辑的镜头。'; return }
    if (editMusic.value.length > 10000 || shot_texts?.some(shot => Object.entries(shot).some(([key, value]) => typeof value === 'string' && value.length > (['camera', 'shot_size'].includes(key) ? 1000 : 10000)))) { error.value = '方案内容过长，请缩短后保存。'; return }
    body.patch = { music_direction: editMusic.value, ...(shot_texts?.length ? { shot_texts } : {}) }
  } else {
    if (Array.from(replanText.value).length > 9800) { error.value = '调整要求最多 9800 字。'; return }
    body.instruction = '请重新规划本次视频方案，保留原商品事实、首帧、时长、画面比例、字幕和声音设置；提供新的创意与镜头方案。' + (replanText.value.trim() ? '\n调整要求：' + replanText.value.trim() : '')
  }
  if (saveCommand({ kind: 'revise', intent: createIntent(body) })) void sendPending()
}
function saveCommand(command: Command) {
  if (storageBlocked.value) return false
  try { sessionStorage.setItem(storageKey.value, JSON.stringify(command)); pending.value = command; return true }
  catch { error.value = '无法保存本次操作记录，请允许浏览器保存会话数据后重试。'; return false }
}
async function sendPending() {
  if (!pending.value || busy.value) return
  const command = pending.value, stamp = revision, key = storageKey.value, taskId = props.taskId, epoch = session.epoch.value
  busy.value = true; error.value = ''
  try {
    const result = command.kind === 'confirm' ? await confirmVideoPlan(taskId, command.intent) : command.kind === 'revise' ? await reviseVideoPlan(taskId, command.intent) : await supplementVideoInputs(taskId, command.intent)
    if (!result || result.kind !== 'video' || typeof result.status !== 'string') throw new ApiError('操作回执尚未确认。')
    if (!alive || stamp !== revision || epoch !== session.epoch.value) return
    sessionStorage.removeItem(key); pending.value = null; confirmationOpen.value = false; inputOpen.value = false; replanOpen.value = false; text.value = ''; emit('changed')
    if (command.kind === 'revise' && props.allowPlanRevision && (JSON.parse(command.intent.body) as VideoPlanRevision).patch) {
      waitingVersion.value = (JSON.parse(command.intent.body) as VideoPlanRevision).plan_version
      await readSavedPlan()
    } else { editOpen.value = false; confirmAfterSave.value = false }
  } catch (e) {
    if (!alive || stamp !== revision || epoch !== session.epoch.value) return
    if (e instanceof ApiError && e.code === 'COMMAND_REJECTED' && e.response?.error.code === 'COMMAND_REJECTED') {
      try { sessionStorage.removeItem(key) } catch { /* A future corrected intent overwrites this rejected record. */ }
      pending.value = null; confirmationOpen.value = false; confirmAfterSave.value = false; error.value = e.message; emit('changed')
    } else error.value = (e instanceof ApiError ? e.message : '操作结果尚未确认。') + ' 请刷新原任务核对，或重试下方原操作。'
  }
  finally { if (alive && stamp === revision) busy.value = false }
}
function confirm() {
  if (!viewedPlan.value || pending.value || busy.value) return
  if (props.allowPlanRevision && (waitingVersion.value !== null || readingPlan.value || Math.max(props.media?.head_plan_version || 0, savedPlan.value?.plan_version || 0) > viewedPlan.value.plan_version)) { error.value = '方案已更新，请重新查看当前方案。'; return }
  if (saveCommand({ kind: 'confirm', intent: createIntent({ plan_version: viewedPlan.value.plan_version }) })) void sendPending()
}
function sendInputs() {
  if (!text.value.trim()) { error.value = '请填写需要补充的商品资料。'; return }
  if (Array.from(text.value.trim()).length > 10000) { error.value = '补充资料最多 10000 字，请修改后提交。'; return }
  if (pending.value || busy.value) return
  if (saveCommand({ kind: 'inputs', intent: createIntent({ text: text.value.trim() }) })) void sendPending()
}
</script>
<template>
  <section v-if="media?.kind === 'video'" class="video-task-panel" aria-label="视频创作进度">
    <p class="video-stage" role="status">{{ stage }}</p>
    <template v-if="media.status === 'awaiting_confirmation'"><p>视频方案已准备好，确认后继续生成。</p><div class="plan-actions"><UiButton class="button primary" type="button" data-view-plan :disabled="busy || !!pending" @click="viewPlan">查看并确认方案</UiButton><template v-if="allowPlanRevision"><UiButton class="button" type="button" data-edit-plan :disabled="busy || !!pending" @click="openRevision(true)">编辑方案</UiButton><UiButton class="button" type="button" data-replan :disabled="busy || !!pending" @click="openRevision(false)">重新生成方案</UiButton></template></div></template>
    <template v-else-if="media.status === 'awaiting_input'"><p>需要补充以下资料后继续规划：</p><ul v-if="questions.length"><li v-for="(question, index) in questions" :key="index">{{ question }}</li></ul><UiButton class="button" type="button" data-open-inputs :disabled="busy || !!pending" @click="inputOpen = true">补充资料</UiButton></template>
    <p v-else-if="['pending', 'planning', 'queued'].includes(media.status || '')">先规划视频，方案完成后需要你确认，届时才继续生成。</p>
    <p v-if="error" class="field-error" role="alert">{{ error }}</p>
    <p v-if="waitingVersion !== null && !editOpen" role="status">正在读取已保存的新方案… <UiButton class="button" type="button" data-read-saved-plan :disabled="readingPlan || busy" @click="readSavedPlan">重新读取</UiButton></p>
    <div v-if="pending" class="command-recovery"><p>上次{{ pending.kind === 'confirm' ? '方案确认' : pending.kind === 'revise' ? '方案修改' : '资料补充' }}结果尚未确认，原操作记录已保留。</p><UiButton class="button" type="button" data-retry-command :disabled="busy" @click="sendPending">{{ busy ? '正在核对原操作…' : '核对并重试原操作' }}</UiButton></div>
    <AppDrawer v-model:open="planOpen" title="视频创作方案">
      <template v-if="viewedPlan"><p>方案版本 {{ viewedPlan.plan_version }}</p><dl class="detail-list"><dt>创意方向</dt><dd>{{ viewedPlan.document.creative }}</dd><dt>目标人群</dt><dd>{{ viewedPlan.document.audience }}</dd><dt>商品卖点</dt><dd><ul><li v-for="point in viewedPlan.document.selling_points" :key="point">{{ point }}</li></ul></dd><dt>视频时长</dt><dd>{{ viewedPlan.document.duration_seconds }} 秒</dd><dt>画面比例</dt><dd>{{ viewedPlan.document.aspect_ratio }}</dd><dt>字幕</dt><dd>{{ viewedPlan.document.subtitles ? '开启' : '关闭' }}</dd><dt>旁白</dt><dd>{{ viewedPlan.document.voiceover ? '开启' : '关闭' }}</dd><dt>音乐</dt><dd>{{ viewedPlan.document.music ? '开启' : '关闭' }}<template v-if="viewedPlan.document.music_direction"> · {{ viewedPlan.document.music_direction }}</template></dd><template v-for="(label, key) in visualLabels" :key="key"><template v-if="viewedPlan.document.shared_visual?.[key]"><dt>{{ label }}</dt><dd>{{ viewedPlan.document.shared_visual[key] }}</dd></template></template></dl>
        <section v-for="(shot, index) in viewedPlan.document.shots" :key="shot.shot_id || index" class="plan-shot"><h3>镜头 {{ index + 1 }}</h3><dl class="detail-list"><template v-for="(label, key) in shotLabels" :key="key"><template v-if="hasDisplayValue(shot[key as keyof typeof shot])"><dt>{{ label }}</dt><dd>{{ shot[key as keyof typeof shot] }}</dd></template></template></dl></section>
      </template><template #actions><UiButton v-if="allowPlanRevision" class="button" type="button" data-drawer-edit-plan :disabled="busy || !!pending || waitingVersion !== null" @click="openRevision(true)">编辑方案</UiButton><UiButton class="button primary" type="button" data-confirm-plan :disabled="busy || !!pending || media?.status !== 'awaiting_confirmation'" @click="askConfirmation">确认此方案</UiButton></template>
    </AppDrawer>
    <AppDialog :open="confirmationOpen" @update:open="closeConfirmation" title="确认视频方案" purpose="charge"><p>将按方案版本 {{ viewedPlan?.plan_version }} 继续生成视频。本任务已冻结积分，本次确认不会再次收费。</p><p>完整成果保存后消费；等待确认期间积分保持冻结。</p><p v-if="error" class="field-error" role="alert">{{ error }}</p><template #actions><UiButton class="button primary" type="button" data-send-confirmation :disabled="busy || !!pending" @click="confirm">{{ busy ? '正在确认…' : '确认并继续生成' }}</UiButton></template></AppDialog>
    <AppDrawer :open="editOpen" @update:open="closeEditor" title="编辑视频方案" purpose="edit">
      <form class="form-stack" @submit.prevent="sendRevision(true)"><p class="field-hint">方案版本 {{ viewedPlan?.plan_version }} · {{ editDirty ? "有未保存修改" : "已保存" }}</p><section v-for="(shot, index) in editShots" :key="shot.shot_id || index" class="plan-shot plan-shot-editor"><h3>镜头 {{ index + 1 }}</h3><label v-for="(label, key) in editableShotLabels" :key="key" :for="taskId + '-shot-' + index + '-' + key">{{ label }}<UiInput :id="taskId + '-shot-' + index + '-' + key" v-model="shot[key]" type="textarea" :rows="key === 'content' ? 3 : 2" :maxlength="['camera', 'shot_size'].includes(key) ? 1000 : 10000" :disabled="busy || !!pending || waitingVersion !== null || readingPlan" :data-shot-content="key === 'content' ? index : undefined" /></label></section><label :for="taskId + '-edit-music'">音乐方向<UiInput :id="taskId + '-edit-music'" v-model="editMusic" type="textarea" rows="2" maxlength="10000" :disabled="busy || !!pending || waitingVersion !== null || readingPlan" /></label><p v-if="error" class="field-error" role="alert">{{ error }}</p></form>
      <p v-if="waitingVersion !== null" role="status">正在读取已保存的新方案… <UiButton class="button text-button" :disabled="readingPlan || busy" @click="readSavedPlan">重新读取</UiButton></p><template #actions><UiButton class="button" type="button" data-save-plan :disabled="busy || !!pending || waitingVersion !== null || readingPlan" @click="confirmAfterSave = false; sendRevision(true)">{{ busy ? '正在保存…' : '保存方案' }}</UiButton><UiButton v-if="allowPlanRevision" class="button primary" type="button" data-edit-confirm-plan :disabled="busy || !!pending || waitingVersion !== null || readingPlan" @click="confirmEditedPlan">确认方案</UiButton></template>
    </AppDrawer>
    <AppDialog v-model:open="replanOpen" title="重新生成视频方案" purpose="edit"><p>重新规划后，确认新方案再生成视频。</p><label :for="taskId + '-replan-text'">调整要求 <small>选填</small></label><UiInput :id="taskId + '-replan-text'" v-model="replanText" type="textarea" rows="4" maxlength="9800" placeholder="描述希望调整的创意或镜头" :disabled="busy || !!pending" /><p v-if="error" class="field-error" role="alert">{{ error }}</p><template #actions><UiButton class="button primary" type="button" data-send-replan :disabled="busy || !!pending" @click="sendRevision(false)">{{ busy ? '正在提交…' : '重新生成方案' }}</UiButton></template></AppDialog>
    <AppDrawer v-model:open="inputOpen" title="补充视频资料" purpose="edit"><form :id="'video-input-' + taskId" class="form-stack" @submit.prevent="sendInputs"><ul v-if="questions.length"><li v-for="(question, index) in questions" :key="index">{{ question }}</li></ul><label :for="'video-text-' + taskId">补充资料 <small>必填</small></label><UiInput type="textarea" :id="'video-text-' + taskId" v-model="text" rows="6" maxlength="10000" required data-initial-focus :disabled="busy || !!pending" /><p>仅补充真实商品信息，提交后在原任务内继续规划，不会新建收费任务。</p><p v-if="error" class="field-error" role="alert">{{ error }}</p></form><template #actions><UiButton class="button primary" type="submit" :form="'video-input-' + taskId" data-send-inputs :disabled="busy || !!pending" @click.prevent="sendInputs">{{ busy ? '正在提交…' : '提交补充资料' }}</UiButton></template></AppDrawer>
  </section>
</template>
<style scoped>
.video-task-panel { margin:16px 0; padding:14px 0; border-top:1px solid var(--color-border); border-bottom:1px solid var(--color-border); font-size:14px; overflow-wrap:anywhere }
.video-task-panel p { line-height:1.8; margin:0 0 12px }
.video-stage { font-weight:600 }
.video-task-panel li { margin:6px 0; line-height:1.7 }
.command-recovery { margin-top:12px; color:var(--color-warning) }
.plan-shot { margin-top:24px; padding-top:16px; border-top:1px solid var(--color-border) }
.plan-shot h3 { font-size:16px; margin:0 0 12px }
.detail-list dd { white-space:pre-wrap; overflow-wrap:anywhere }
.detail-list ul { padding-left:20px; margin:0 }
.plan-actions { display:flex; align-items:center; flex-wrap:wrap; gap:8px }
.plan-shot-editor { display:grid; gap:12px; margin-top:12px; padding-top:16px }
.plan-shot-editor label { display:grid; gap:6px; font-size:13px; font-weight:500 }
.plan-shot-editor h3 { margin-bottom:0; font-size:14px }
</style>
