<script setup lang="ts">
import { MAX_PRODUCT_REFERENCES } from './materialLimits'
import UiButton from '../../components/ui/UiButton.vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import UiInput from '../../components/ui/UiInput.vue'
import { computed, onScopeDispose, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Schema } from '../../types/api'
import { listAgents, getVideoOptions, quote as fetchQuote } from '../../api/catalog'
import { createConversation, createProductVersion, getProductVersion } from '../../api/conversations'
import { uploadFile, fileContentUrl } from '../../api/files'
import { submitTaskIntent, getRegenerationQuote, type RegenerationQuote } from '../../api/tasks'
import { getWork } from '../../api/works'
import { ApiError, createIntent } from '../../api/client'
import { session } from '../auth/session'
import { draftFor, taskDraftFor, restoreTaskDraft, moveDraft, copyTaskDraft, setSourceDraft, type Draft } from './drafts'
import { useTaskStream } from './useTaskStream'
import AgentSelector from '../../components/AgentSelector.vue'
import QuotePanel from '../../components/QuotePanel.vue'
import TaskCard from '../../components/TaskCard.vue'
import TaskHistory from './TaskHistory.vue'
import AppDrawer from '../../components/AppDrawer.vue'
import AppDialog from '../../components/AppDialog.vue'
import MediaChoices from './MediaChoices.vue'
import TextChoices from './TextChoices.vue'
import { textParameters, validateTextParameters } from './textParameters'
import { videoParameters, validateVideoParameters, type VideoOptions } from './videoParameters'
import { productLabels, productExamples, fieldLabel, labeledEntries } from './display'
import { productTypes, productType, productFormGroups, longProductFields, editableProduct } from './productTypes'

const route = useRoute(), router = useRouter()
const conversationId = computed(() => String(route.params.conversationId || ''))
const draft = computed(() => {
  const base = draftFor(conversationId.value)
  const taskId = snapshotTaskId.value
  // A pending charge must remain reachable through any link in its conversation.
  return base.pending || !taskId ? base : taskDraftFor(conversationId.value, taskId)
})
const agents = ref<Schema<'AgentVersion'>[]>([])
const catalogBusy = ref(true)
const agent = computed(() => agents.value.find(a => a.agent_id === draft.value.agentId))
const settings = computed(() => draft.value.agents[draft.value.agentId])
const stream = useTaskStream(conversationId)
const { tasks, details, fragments, connectionState } = stream
const selectingTaskId = ref('')
const requestedTaskId = computed(() => typeof route.query?.task === 'string' ? route.query.task : '')
const selectedTaskId = computed(() => requestedTaskId.value || stream.latestTaskId?.value || tasks.value[0]?.task_id || '')
const selectedTask = computed(() => {
  const detail = details.value[selectedTaskId.value]
  return detail?.conversation_id === conversationId.value ? detail : undefined
})
const snapshotTaskId = computed(() => {
  if (requestedTaskId.value) return requestedTaskId.value
  const id = selectedTaskId.value, detail = details.value[id]
  return id && (!detail || detail.conversation_id === conversationId.value) ? id : ''
})
const taskReadOnly = computed(() => !!snapshotTaskId.value && !draftFor(conversationId.value).pending)
const snapshotReady = ref(false)
const restoredSnapshots = new WeakSet<Draft>()
const resultsLoading = computed(() => !!conversationId.value && !selectedTask.value &&
  (selectingTaskId.value === selectedTaskId.value && !!selectingTaskId.value ||
    ['connecting', 'recovering'].includes(connectionState.value)))
async function refreshResults(taskId?: string) {
  if (!taskId) { await stream.reconnect(); return }
  const ownerConversation = conversationId.value
  selectingTaskId.value = taskId
  try {
    await router.replace({ path: route.path, query: { ...route.query, task: taskId } })
    if (conversationId.value === ownerConversation) await stream.refreshTask(taskId)
  } finally { if (selectingTaskId.value === taskId) selectingTaskId.value = '' }
}
const error = ref(''), quote = ref<Schema<'Quote'> | null>(null), quoteBusy = ref(false), uploadBusy = ref(false)
const regenerationQuote = ref<RegenerationQuote | null>(null)
const regenerationSourceId = computed(() => !taskReadOnly.value ? draft.value.regenerationSourceId : undefined)
const displayQuote = computed(() => quote.value && regenerationQuote.value ? { ...quote.value, credits: regenerationQuote.value.credits } : quote.value)
const confirmedCredits = computed(() => confirmed.value?.regeneration?.expected_credits ?? confirmed.value?.confirmed_quote.credits ?? 0)
const freeRegeneration = computed(() => !!confirmed.value?.regeneration && draft.value.confirmedFreeRegeneration === true && confirmedCredits.value === 0)
const productOpen = ref(false), productSaving = ref(false), productFields = ref<Record<string, string>>({})
const materialUpload = ref<HTMLInputElement>()
const productError = ref('')
const originalProduct = ref<Record<string, unknown>>({})
const productGroups = computed(() => productFormGroups(productFields.value.product_type).map(group => ({ ...group,
  fields: group.fields.map(field => field === 'description' && agent.value?.input_support.product_required_fields.includes('sellingPoints') &&
    !agent.value.input_support.product_required_fields.includes('description') ? 'sellingPoints' : field),
})))
const productRestoring = ref(false), productRestoreError = ref('')
let productRestoreRevision = 0
const extraProductFields = computed(() => [...new Set([...Object.keys(originalProduct.value), ...(agent.value?.input_support.product_required_fields || [])])].filter(key => !productGroups.value.some(group => group.fields.includes(key))))
const productEntries = computed(() => labeledEntries(editableProduct(draft.value.product?.product || {}), 'product'))
const confirmationOpen = ref(false)
const preparations = ref(new Set<Draft>())
const preparing = computed(() => preparations.value.has(draft.value))
const submissions = ref(new Set<Draft>())
const submitting = computed(() => submissions.value.has(draft.value))
const confirmed = computed({ get: () => draft.value.confirmed ?? null, set: value => { draft.value.confirmed = value } })
const pending = computed({ get: () => draft.value.pending ?? null, set: value => { draft.value.pending = value } })
// Pending is authoritative even for drafts saved before an in-flight page exit.
const uncertain = computed(() => !!pending.value && !submitting.value)
let alive = true, quoteVersion = 0, quoteTimer: ReturnType<typeof setTimeout> | undefined
const epoch = session.epoch.value
const active = () => alive && epoch === session.epoch.value
onScopeDispose(() => { alive = false; quoteVersion++; clearTimeout(quoteTimer) })
async function restoreHistoryProduct() {
  const stamp = ++productRestoreRevision, id = snapshotTaskId.value, owner = draft.value, source = selectedTask.value
  productRestoring.value = false; productRestoreError.value = ''; snapshotReady.value = false
  if (!taskReadOnly.value || !id || !source?.agent_id || owner.pending) return
  if (restoredSnapshots.has(owner)) { snapshotReady.value = true; return }
  const eligible = () => active() && stamp === productRestoreRevision && snapshotTaskId.value === id && draft.value === owner &&
    taskReadOnly.value && !owner.pending
  productRestoring.value = true
  try {
    const product = await getProductVersion(source.input.product_version)
    if (eligible()) { restoreTaskDraft(owner, source, product); restoredSnapshots.add(owner); snapshotReady.value = true }
  } catch { if (eligible()) productRestoreError.value = '历史商品资料暂时无法读取，请重试。' }
  finally { if (stamp === productRestoreRevision) productRestoring.value = false }
}
watch([conversationId, snapshotTaskId, () => selectedTask.value?.input.product_version,
  () => draft.value.pending], () => { void restoreHistoryProduct() }, { immediate: true, flush: 'sync' })
void listAgents().then(value => { if (active()) agents.value = value }).catch(() => { if (active()) error.value = '暂时无法读取可用 Agent。' }).finally(() => { if (active()) catalogBusy.value = false })
watch([agents, conversationId, selectedTaskId], () => {
  if (selectedTaskId.value || requestedTaskId.value || draft.value.agentId || draft.value.pending || draft.value.sourceWorkId) return
  const copies = agents.value.filter(item => item.enabled && item.kind === 'copy')
  if (copies.length === 1) draft.value.agentId = copies[0].agent_id
}, { immediate: true })
watch([draft, () => draft.value.agentId], ([owner, id]) => {
  if (!id) return
  owner.agents[id] ??= { specId: '', instruction: '', parameters: {} }
}, { immediate: true })
const mediaProtocol = computed(() => agent.value?.protocol_version || '')
const materialLimit = computed(() => Math.min(MAX_PRODUCT_REFERENCES, agent.value?.input_support.max_materials ?? 0))
const videoOptions = ref<VideoOptions | null>(null), videoOptionsBusy = ref(false), videoOptionsError = ref('')
let videoOptionsVersion = 0
async function loadVideoOptions() {
  const stamp = ++videoOptionsVersion
  videoOptionsBusy.value = true; videoOptionsError.value = ''
  try {
    const options = await getVideoOptions()
    if (active() && stamp === videoOptionsVersion) videoOptions.value = options
  } catch (e) {
    if (active() && stamp === videoOptionsVersion) {
      videoOptions.value = null
      videoOptionsError.value = e instanceof ApiError ? e.message : '视频参数暂时无法读取，请重试。'
    }
  } finally { if (active() && stamp === videoOptionsVersion) videoOptionsBusy.value = false }
}
watch([mediaProtocol, taskReadOnly, conversationId], () => {
  if (mediaProtocol.value === 'video-agent-v1' && !taskReadOnly.value) void loadVideoOptions()
}, { immediate: true })
const creationParameters = computed((): Record<string, string | number | boolean> => {
  const parameters = settings.value?.parameters || {}
  if (mediaProtocol.value === 'text-agent-v1') {
    const values = textParameters(parameters)
    if (!taskReadOnly.value && !regenerationSourceId.value) delete values.audience
    return values
  }
  if (mediaProtocol.value === 'image-agent-v1') return { platform: String(parameters.platform || ''), output_type: String(parameters.output_type || '') }
  if (mediaProtocol.value === 'video-agent-v1') return videoParameters(parameters)
  return {}
})
const input = computed<Schema<'InputSnapshot'> | null>(() => draft.value.product && settings.value ? { product_version: draft.value.product.version, product: draft.value.product.product, instruction: taskReadOnly.value || regenerationSourceId.value ? settings.value.instruction : '', parameters: creationParameters.value, material_versions: draft.value.materials } : null)
const validation = computed(() => {
  if (taskReadOnly.value) return '已创建任务的输入为只读，请基于此任务新建草稿。'
  if (requestedTaskId.value && !draft.value.sourceTaskId && !pending.value) return '请先读取所选任务的创作资料。'
  if (!agent.value) return '请选择本次创作的类型。'
  if (!draft.value.product) return '请先保存商品资料。'
  if (draft.value.materials.length > MAX_PRODUCT_REFERENCES) return `商品参考图最多支持 ${MAX_PRODUCT_REFERENCES} 张，请移除多余引用后生成。`
  if (mediaProtocol.value === 'text-agent-v1') {
    const textError = validateTextParameters(creationParameters.value)
    if (textError) return textError
  }
  if (['image-agent-v1', 'video-agent-v1'].includes(mediaProtocol.value) && !String(draft.value.product.product.category || '').trim()) return '请补充商品分类。'
  if (mediaProtocol.value === 'image-agent-v1') {
    if (!settings.value?.parameters.platform) return '请选择目标平台。'
    if (!settings.value?.parameters.output_type) return '请选择图片用途。'
  }
  if (mediaProtocol.value === 'video-agent-v1' && !draft.value.materials.some(m => m.file_id === settings.value?.parameters.first_frame_file_id)) return '请从商品图片中选择视频首帧。'
  if (mediaProtocol.value === 'video-agent-v1') {
    if (videoOptionsBusy.value) return '正在读取视频参数。'
    if (!videoOptions.value) return videoOptionsError.value || '请先读取视频参数。'
    const videoError = validateVideoParameters(creationParameters.value, videoOptions.value)
    if (videoError) return videoError
  }
  for (const field of agent.value.input_support.product_required_fields) if (!String(draft.value.product.product[field] ?? '').trim()) return '请补充商品资料：' + fieldLabel(field, 'product', agent.value.input_support.product_required_fields.indexOf(field))
  if (draft.value.missingMaterials) return '来源素材已不可用，请补传 ' + draft.value.missingMaterials + ' 张商品图片。'
  if (draft.value.materials.length < agent.value.input_support.min_materials) return '请上传至少 ' + agent.value.input_support.min_materials + ' 张商品图片。'
  if (draft.value.materials.length > agent.value.input_support.max_materials) return '商品图片超过当前 Agent 支持数量。'
  return ''
})
watch(() => JSON.stringify({ input: input.value, agent: agent.value?.agent_id, source: regenerationSourceId.value, video_options_ready: mediaProtocol.value === 'video-agent-v1' && !!videoOptions.value && !videoOptionsBusy.value }), () => {
  quote.value = null; regenerationQuote.value = null; quoteBusy.value = false; quoteVersion++; clearTimeout(quoteTimer)
  if (!validation.value) quoteTimer = setTimeout(() => { void refreshQuote() }, 200)
}, { immediate: true })
async function refreshQuote() {
  clearTimeout(quoteTimer)
  quoteTimer = undefined
  const stamp = ++quoteVersion
  if (validation.value || !input.value) return
  quoteBusy.value = true
  try {
    const body = { agent_id: agent.value!.agent_id, input: input.value }
    if (regenerationSourceId.value) {
      const value = await getRegenerationQuote(regenerationSourceId.value, body)
      if (active() && stamp === quoteVersion) { quote.value = value.quote; regenerationQuote.value = value }
    } else {
      const value = await fetchQuote(body)
      if (active() && stamp === quoteVersion) { quote.value = value; regenerationQuote.value = null }
    }
  }
  catch (e) { if (active() && stamp === quoteVersion) error.value = e instanceof ApiError ? e.message : '当前报价无法读取。' }
  finally { if (active() && stamp === quoteVersion) quoteBusy.value = false }
}
const productFieldText = (value: unknown) => typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value ?? '')
function editProduct() {
  if (taskReadOnly.value) return
  productRestoreRevision++; productError.value = ''
  originalProduct.value = editableProduct(draft.value.product?.product || {}, agent.value?.input_support.product_required_fields)
  productFields.value = Object.fromEntries(Object.entries(originalProduct.value).map(([key, value]) => [key, productFieldText(value)]))
  for (const key of new Set([...productGroups.value.flatMap(group => group.fields), ...(agent.value?.input_support.product_required_fields || [])])) productFields.value[key] ??= ''
  productOpen.value = true
}
async function saveProduct() {
  if (taskReadOnly.value) return
  if (!productFields.value.name?.trim()) { productError.value = '请填写商品名称。'; return }
  const type = productType(productFields.value.product_type)
  if (!type) { productError.value = '请选择商品类型。'; return }
  productSaving.value = true; const owner = draft.value
  const keys = new Set([...productGroups.value.flatMap(group => group.fields), ...extraProductFields.value])
  const values = Object.fromEntries([...keys].flatMap(key => {
    const value = (productFields.value[key] || '').trim()
    if (!value) return []
    return [[key, typeof originalProduct.value[key] === 'object' && value === productFieldText(originalProduct.value[key]) ? originalProduct.value[key] : value]]
  }))
  values.category ||= type.label
  try { const product = await createProductVersion({ product: editableProduct(values, agent.value?.input_support.product_required_fields), product_id: owner.product?.product_id }); if (active()) { owner.product = product; productOpen.value = false; error.value = ''; productError.value = '' } }
  catch (e) { if (active()) productError.value = e instanceof ApiError ? e.message : '资料保存失败。' }
  finally { productSaving.value = false }
}
async function upload(event: Event) {
  const control = event.target as HTMLInputElement, file = control.files?.[0]
  if (!file || uploadBusy.value || taskReadOnly.value || !agent.value) return
  const owner = draft.value, replacing = agent.value.input_support.max_materials === 1 && owner.materials.length > 0
  if (!replacing && owner.materials.length >= materialLimit.value) { error.value = `最多上传 ${materialLimit.value} 张商品图片。`; control.value = ''; return }
  uploadBusy.value = true
  try { const value = await uploadFile(file); if (active()) { if (replacing) owner.materials.splice(0, 1, value); else owner.materials.push(value); owner.missingMaterials = Math.max(0, owner.missingMaterials - 1); error.value = '' } }
  catch (e) { if (active()) error.value = e instanceof ApiError ? e.message : '图片上传失败。' }
  finally { uploadBusy.value = false; control.value = '' }
}
async function startTaskDraft() {
  if (!taskReadOnly.value || !snapshotReady.value || preparing.value) return
  const owner = draft.value, sourceTaskId = snapshotTaskId.value
  preparations.value.add(owner); error.value = ''
  try {
    const item = await createConversation({ title: '重新创作 · ' + String(owner.product?.product.name || '商品') })
    if (!active() || draft.value !== owner) return
    const target = copyTaskDraft(owner, item.conversation_id)
    target.sourceTaskId = sourceTaskId
    target.regenerationSourceId = selectedTask.value?.task.state === 'SUCCEEDED' && ['copy', 'image'].includes(agent.value?.kind || '') ? sourceTaskId : undefined
    await router.push('/workspace/' + item.conversation_id)
  } catch (e) { if (active() && draft.value === owner) error.value = e instanceof ApiError ? e.message : '无法创建新草稿，请重试。' }
  finally { preparations.value.delete(owner) }
}
async function prepare() {
  if (taskReadOnly.value) { await startTaskDraft(); return }
  if (preparing.value) return
  const owner = draft.value
  preparations.value.add(owner)
  try {
  error.value = validation.value
  if (error.value || !input.value || !agent.value || pending.value) return
  if (!quote.value) await refreshQuote()
  if (!active() || draft.value !== owner || !quote.value) return
  const snapshot = JSON.parse(JSON.stringify({ agent_id: agent.value.agent_id, input: input.value, confirmed_quote: quote.value,
    ...(regenerationSourceId.value && regenerationQuote.value ? { regeneration: { source_task_id: regenerationSourceId.value, expected_credits: regenerationQuote.value.credits, expected_used: regenerationQuote.value.free_regenerations_used } } : {}) }))
  if (!conversationId.value) { const item = await createConversation({ title: String(owner.product?.product.name || '新会话') }); if (!active() || draft.value !== owner) return; moveDraft('', item.conversation_id); await router.push('/workspace/' + item.conversation_id) }
  confirmed.value = { ...snapshot, conversation_id: conversationId.value }
  draft.value.confirmedFreeRegeneration = !!regenerationQuote.value?.eligible && regenerationQuote.value.free_regenerations_remaining > 0
  confirmationOpen.value = true
  } catch (e) { if (active() && draft.value === owner) error.value = e instanceof ApiError ? e.message : '无法准备本次创作，请重试。' }
  finally { preparations.value.delete(owner) }
}
async function submit() {
  if (!confirmed.value || submitting.value) return
  pending.value ??= createIntent(confirmed.value)
  const owner = draft.value
  const intent = pending.value
  owner.uncertain = true
  submissions.value.add(owner); error.value = ''
  try {
    const admitted = await submitTaskIntent(intent)
    if (!active() || owner.pending?.key !== intent.key) return
    const taskId = admitted?.task?.task_id
    if (typeof taskId !== 'string' || !taskId.trim()) throw new ApiError('受理回执不完整，请核对原请求。')
    const wasDisplayed = owner === draft.value
    owner.pending = null; owner.uncertain = false
    if (wasDisplayed) {
      confirmationOpen.value = false
      await refreshResults(taskId)
    } else await stream.refreshTask(taskId)
    await session.refreshAccount()
  } catch (e) {
    if (!active() || owner.pending?.key !== intent.key) return
    // Only structured admission rejections prove this intent was not accepted.
    // Proxy/5xx, auth, idempotency conflicts and unreadable success remain uncertain.
    const rejected = e instanceof ApiError && e.status >= 400 && e.status < 500 &&
      e.response?.error.code === e.code && ['QUOTE_STALE', 'INPUT_INVALID', 'SPEC_DISABLED',
        'INSUFFICIENT_CREDITS', 'CAPACITY_INSUFFICIENT', 'FEATURE_NOT_ENABLED', 'MATERIAL_UNAVAILABLE', 'RATE_LIMITED'].includes(e.code ?? '')
    if (rejected) {
      const wasDisplayed = owner === draft.value
      owner.pending = null; owner.uncertain = false
      if (wasDisplayed) {
        confirmationOpen.value = false
        error.value = e.code === 'QUOTE_STALE' ? '报价已更新，请核对费用并重新确认。'
          : e.code === 'CAPACITY_INSUFFICIENT' ? '当前存储空间不足，暂时无法创建任务。请联系管理员处理后重试。' : e.message
        // Ending a base-draft recovery may reveal the selected task's own draft.
        // Never refresh that task's quote on behalf of the rejected original intent.
        if (e.code === 'QUOTE_STALE' && owner === draft.value) { quote.value = null; await refreshQuote() }
      }
    }
    else { owner.uncertain = true; if (owner === draft.value) error.value = '提交结果尚未确认。请核对原任务或用同一请求重试，不会创建新的意图。' }
  } finally { submissions.value.delete(owner) }
}
async function retry() {
  const owner = draft.value, intent = owner.pending
  if (!intent) return
  await stream.reconnect()
  if (!active() || owner !== draft.value || owner.pending?.key !== intent.key) return
  owner.confirmed = JSON.parse(intent.body)
  confirmationOpen.value = true
}
async function regenerate(work: Schema<'WorkDetail'>) {
  const owner = draft.value, taskId = selectedTaskId.value
  if (preparations.value.has(owner)) return
  const current = () => active() && draft.value === owner && selectedTaskId.value === taskId
  preparations.value.add(owner)
  try {
    const latest = await getWork(work.work_id)
    if (!current()) return
    const product = await getProductVersion(latest.source.input.product_version)
    if (!current()) return
    const conversation = await createConversation({ title: '重新创作 · ' + String(product.product.name || '商品') })
    if (!current()) return
    setSourceDraft(conversation.conversation_id, latest, product)
    await router.push('/workspace/' + conversation.conversation_id)
  } catch (e) { if (current()) error.value = e instanceof ApiError ? e.message : '无法读取来源资料。' }
  finally { preparations.value.delete(owner) }
}
watch(() => tasks.value.map(t => t.task_id + ':' + t.settlement_state).sort().join(','), () => { void session.refreshAccount().catch(() => {}) })
watch([conversationId, requestedTaskId], () => { confirmationOpen.value = false; productOpen.value = false; error.value = '' }, { flush: 'sync' })
</script>
<template>
  <div class="workspace-grid">
    <section class="creation-panel panel" aria-label="创作配置">
      <fieldset :disabled="taskReadOnly || catalogBusy || preparing || submitting || !!pending || productRestoring" class="composer-tabs"><AgentSelector :key="conversationId + snapshotTaskId" v-model="draft.agentId" :agents="agents" /></fieldset>
      <div v-if="error || uncertain" class="composer-recovery"><p v-if="error" class="field-error" role="alert">{{ error }}</p><UiButton v-if="uncertain" class="button" type="button" @click="retry">核对并重试原请求</UiButton></div>
      <div v-if="productRestoreError" class="composer-recovery"><p class="field-error" role="alert">{{ productRestoreError }}</p><UiButton class="button text-button" type="button" @click="restoreHistoryProduct">重试回填资料</UiButton></div>
      <fieldset :disabled="taskReadOnly || catalogBusy || preparing || submitting || !!pending || productRestoring" class="composer-form">
      <div class="composer-scroll form-stack" tabindex="0" aria-label="创作资料与设置">
      <p v-if="taskReadOnly" class="source-note">以下为此任务提交时的资料与设置。基于此任务再生成将创建独立草稿，原任务与成果保留。</p>
      <p v-else-if="draft.sourceWorkId" class="source-note">原作品输入已带回，可编辑。确认本次费用后创建新任务，原成果保留。</p>
      <p v-else-if="draft.sourceTaskId" class="source-note">已带入此任务的商品、素材与创作设置，可编辑后再生成。原任务与成果保留。</p>
      <p v-if="catalogBusy" role="status">正在读取可用创作能力…</p>
        <section class="creation-section product-section" aria-label="商品资料">
          <div class="section-heading"><h3><svg class="section-symbol" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6 M9 16h6" /></svg>商品资料</h3><UiButton v-if="!taskReadOnly" class="button text-button" type="button" @click="editProduct">{{ draft.product?.product.name ? '编辑资料' : '填写资料' }}</UiButton></div>
          <dl v-if="productEntries.length" class="product-details"><div v-for="entry in productEntries" :key="entry.key" :class="{ 'product-wide': ['name', 'description', 'sellingPoints', 'notes', 'audience', 'scene', 'package'].includes(entry.key) || entry.label.length > 5 || String(entry.value).length > 24 }"><dt>{{ entry.label }}</dt><dd>{{ entry.value }}</dd></div></dl>
          <p v-else class="product-empty" :role="productRestoring ? 'status' : undefined">{{ productRestoring ? '正在回填历史商品资料…' : '添加商品资料，让创作更贴合商品。' }}</p>
          <div class="product-materials" role="group" aria-label="商品图片">
          <p class="material-label">参考图片 <small v-if="agent">{{ agent.input_support.min_materials > 0 ? '（必填）' : '（选填）' }} · {{ draft.materials.length }} / {{ materialLimit }}</small></p>
          <p v-if="draft.missingMaterials" class="field-error" role="alert">来源素材已不可用，请补传 {{ draft.missingMaterials }} 张商品图片。</p>
          <div v-for="(material, index) in draft.materials" :key="material.file_id" class="material-row">
            <img :src="fileContentUrl(material.file_id)" :alt="'商品参考图 ' + (index + 1)" />
            <div class="material-copy"><strong>商品参考图 {{ index + 1 }}</strong><small>已上传</small></div>
            <div v-if="!taskReadOnly" class="material-actions"><UiButton v-if="agent?.input_support.max_materials === 1" class="button replace-material" type="button" :disabled="uploadBusy" @click="materialUpload?.click()">更换图片</UiButton><UiButton class="button text-button" type="button" @click="draft.materials.splice(index, 1)">移除引用</UiButton></div>
          </div>
          <div v-if="!taskReadOnly && (!draft.materials.length || agent?.input_support.max_materials !== 1)" class="upload-control"><p v-if="!draft.materials.length">尚未选择图片</p><UiButton class="button" type="button" :disabled="uploadBusy || !agent || agent.input_support.max_materials !== 1 && draft.materials.length >= materialLimit" @click="materialUpload?.click()">{{ draft.materials.length ? '添加商品图片' : '选择图片' }}</UiButton></div>
          <input id="material-upload" ref="materialUpload" hidden aria-label="上传商品图片" type="file" accept="image/png,image/jpeg,image/webp" :disabled="uploadBusy || !agent || agent.input_support.max_materials !== 1 && draft.materials.length >= materialLimit" @change="upload" />
          <p v-if="uploadBusy" role="status">正在保存图片…</p>
          </div>
        </section>
        <p v-if="mediaProtocol === 'video-agent-v1' && !taskReadOnly && videoOptionsBusy" role="status">正在读取视频参数…</p>
        <p v-if="mediaProtocol === 'video-agent-v1' && !taskReadOnly && videoOptionsError" class="field-error" role="alert">{{ videoOptionsError }} <UiButton type="button" class="text-button" @click="loadVideoOptions">重试读取参数</UiButton></p>
        <MediaChoices :disabled="taskReadOnly || catalogBusy || videoOptionsBusy || preparing || submitting || !!pending" v-if="settings" :key="conversationId + snapshotTaskId + draft.agentId + '-media'" :protocol="mediaProtocol" :video-options="taskReadOnly ? null : videoOptions" v-model="settings.parameters" :materials="draft.materials" />
        <TextChoices v-if="settings && mediaProtocol === 'text-agent-v1'" :key="conversationId + snapshotTaskId + draft.agentId + '-text'" v-model="settings.parameters" />

      </div>
      </fieldset>
      <div class="composer-footer form-stack">
        <QuotePanel v-if="!taskReadOnly" :quote="displayQuote" :loading="quoteBusy" />
        <p v-if="!taskReadOnly && regenerationQuote && !quoteBusy" class="regeneration-note" role="status">{{ !regenerationQuote.eligible ? '创作内容已变更或不适用免费额度，本次按当前报价生成。' : regenerationQuote.free_regenerations_remaining > 0 ? '免费重新生成剩余 ' + regenerationQuote.free_regenerations_remaining + ' 次' : '免费次数已用完，再次生成将计费' }}</p>
        <UiButton class="button primary generate-button" type="button" :disabled="catalogBusy || preparing || submitting || !!pending || quoteBusy || uploadBusy || productSaving || productRestoring || taskReadOnly && !snapshotReady || !taskReadOnly && mediaProtocol === 'video-agent-v1' && (videoOptionsBusy || !videoOptions)" @click="prepare">{{ preparing ? (taskReadOnly ? '正在创建新草稿…' : '正在核对本次创作…') : taskReadOnly ? '基于此任务再生成' : '确认费用并生成' }}</UiButton>
      </div>
    </section>
    <section class="task-history panel" aria-label="当前任务产物">
      <div class="history-heading"><h2>任务产物</h2><TaskHistory v-if="selectedTask?.regeneration" :detail="selectedTask" :agents="agents" /></div>
      <div class="results-canvas">
        <TaskCard v-if="selectedTask" :key="selectedTask.task.task_id" :detail="selectedTask" :agent="agents.find(a => a.agent_id === selectedTask!.agent_id)" :fragment="fragments[selectedTask.task.task_id]" @regenerate="regenerate" @media-changed="refreshResults" />
        <div v-else-if="resultsLoading" class="results-skeleton" role="status" aria-label="正在读取任务产物"><div class="skeleton-heading"><span/><span/></div><div class="skeleton-artifact"/><div class="skeleton-actions"><span/><span/></div></div>
        <div v-else-if="requestedTaskId || selectedTaskId" class="empty-state task-unavailable"><span class="empty-state-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 5h14v14H5z M8 9h8 M8 13h5" /></svg></span><h3>暂时无法展示该任务</h3><p>请重新读取，或从最近任务中选择其他任务。</p><UiButton class="button" type="button" @click="stream.reconnect">重新读取任务</UiButton></div>
        <div v-else class="empty-state"><span class="empty-state-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="m3 16 5-5 4 4 4-6 5 7 M8 8h.01" /></svg></span><h3>开始一项新创作</h3><p>准备商品资料并确认费用，生成的文案、图片或视频会集中展示在这里。</p></div>
      </div>
    </section>
  </div>
  <AppDrawer v-model:open="productOpen" title="编辑商品资料" purpose="edit">
    <form id="product-form" class="form-stack product-form" @submit.prevent="saveProduct">
      <p>选择商品类型后填写对应规格。仅填写真实信息，未知规格留空。</p>
      <fieldset v-for="group in productGroups" :key="group.title" class="product-fieldset"><legend>{{ group.title }}</legend><div class="product-fields">
        <div v-for="field in group.fields" :key="field" :class="{ 'wide-field': longProductFields.includes(field) }">
          <label :for="'product-' + field">{{ productLabels[field] }}<span v-if="['name', 'product_type'].includes(field) || agent?.input_support.product_required_fields.includes(field)" class="required-label"> 必填</span></label>
          <UiSelect v-if="field === 'product_type'" id="product-product_type" v-model="productFields.product_type" required><option disabled value="">请选择商品类型</option><option v-for="type in productTypes" :key="type.value" :value="type.value">{{ type.label }}</option></UiSelect>
          <UiInput type="textarea" v-else-if="longProductFields.includes(field)" :id="'product-' + field" :aria-label="productLabels[field] || fieldLabel(field, 'product', extraProductFields.indexOf(field))" v-model="productFields[field]" maxlength="600" rows="3" :placeholder="productExamples[field]" :required="agent?.input_support.product_required_fields.includes(field)" />
          <UiInput v-else :id="'product-' + field" :aria-label="productLabels[field] || fieldLabel(field, 'product', extraProductFields.indexOf(field))" v-model="productFields[field]" :data-initial-focus="field === 'name' ? '' : undefined" maxlength="120" :placeholder="productExamples[field]" :required="field === 'name' || agent?.input_support.product_required_fields.includes(field)" />
        </div>
      </div></fieldset>
      <fieldset v-if="extraProductFields.length" class="product-fieldset"><legend>已有补充资料</legend><div class="product-fields"><div v-for="(field, index) in extraProductFields" :key="field" class="wide-field"><label :for="'product-' + field">{{ fieldLabel(field, 'product', index) }}<span v-if="agent?.input_support.product_required_fields.includes(field)" class="required-label"> 必填</span></label><UiInput type="textarea" :id="'product-' + field" :aria-label="productLabels[field] || fieldLabel(field, 'product', extraProductFields.indexOf(field))" v-model="productFields[field]" rows="3" :required="agent?.input_support.product_required_fields.includes(field)" /></div></div></fieldset>
      <p v-if="productError" class="field-error" role="alert">{{ productError }}</p>
    </form><template #actions><UiButton class="button primary" type="submit" form="product-form" :disabled="productSaving">{{ productSaving ? '正在保存…' : '保存商品资料' }}</UiButton></template>
  </AppDrawer>
  <AppDialog v-model:open="confirmationOpen" :title="freeRegeneration ? '免费重新生成' : confirmedCredits === 0 ? '确认本次生成' : draft.sourceWorkId || draft.sourceTaskId ? '重新生成 · 再次收费' : '确认本次生成'" purpose="charge">
    <p v-if="confirmed && agents.find(a => a.agent_id === confirmed!.agent_id)?.protocol_version === 'video-agent-v1'">视频将先规划方案，需要你查看并确认后才继续生成；本次提交冻结积分，后续确认方案不会再次收费。</p>
    <template v-if="confirmed"><p class="confirmation-product">{{ confirmed.input.product.name }} · {{ agents.find(a => a.agent_id === confirmed!.agent_id)?.name || '创作任务' }}</p><div class="charge-summary"><span>{{ confirmedCredits === 0 ? '本次费用' : '本次将冻结' }}</span><p class="charge-amount">{{ confirmedCredits }} <small>积分</small></p></div><p v-if="freeRegeneration">使用 1 次免费重新生成额度，不冻结或扣除积分。原任务与成果保留。</p><p v-else-if="confirmedCredits === 0">本次报价为 0 积分，不冻结或扣除积分。原任务与成果保留。</p><p v-else-if="draft.sourceWorkId || draft.sourceTaskId">保留原任务与成果，按当前报价创建新任务并再次收费。</p><p v-if="confirmedCredits > 0">完整成果保存后消费；失败后可重试或主动释放积分。</p>
      <details class="snapshot-disclosure"><summary>查看完整提交内容</summary><dl class="detail-list"><template v-for="entry in labeledEntries(confirmed.input.product, 'product')" :key="entry.key"><dt>{{ entry.label }}</dt><dd>{{ entry.value }}</dd></template><dt>创作指令</dt><dd>{{ confirmed.input.instruction || '按商品资料生成' }}</dd><dt>商品素材</dt><dd>{{ confirmed.input.material_versions.length }} 张</dd></dl></details><p v-if="error" class="field-error" role="alert">{{ error }}</p>
    </template><template #actions><UiButton class="button primary" type="button" :disabled="submitting" @click="submit">{{ submitting ? '正在提交…' : freeRegeneration ? '确认免费生成' : confirmedCredits === 0 ? '确认生成' : '确认并冻结积分' }}</UiButton></template>
  </AppDialog>
</template>
<style scoped>
.workspace-grid { grid-template-rows:minmax(0,1fr); row-gap:12px }
.creation-panel { grid-row:1; padding:0; min-width:0; overflow:hidden; display:flex; flex-direction:column; box-shadow:0 2px 8px color-mix(in srgb,var(--color-text) 3%,transparent) }
.creation-panel .composer-form { display:flex; flex-direction:column; min-height:0; flex:1 }
.creation-panel .composer-tabs { padding:12px; border-bottom:1px solid var(--color-border); flex-shrink:0; background:var(--color-panel) }
.composer-scroll { padding:12px 16px 16px; align-content:start }
.composer-footer { padding:12px 16px; border-top:1px solid var(--color-border); flex-shrink:0; background:var(--color-panel); box-shadow:0 -4px 12px color-mix(in srgb,var(--color-text) 2%,transparent) }
.composer-footer :deep(.quote-panel) { border:0; padding:0 }
.composer-recovery { padding:16px 20px 0; overflow-y:auto; max-height:30%; flex-shrink:0; overflow-wrap:anywhere }
.creation-panel .form-stack { gap:12px }
.product-section { border-top:0; padding-top:0 }
.creation-section .section-heading { margin:0 0 6px; gap:8px }
.creation-section h3 { font-size:14px; font-weight:650 }
.text-button { border:0; background:transparent; padding:4px 0; color:var(--color-muted); font-size:13px }
.product-details { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0 12px; margin:0; font-size:13px }
.product-details>div { display:grid; grid-template-columns:56px minmax(0,1fr); gap:8px; padding:5px 0; align-content:start; line-height:1.65 }
.product-details>.product-wide { grid-column:1 / -1 }
.product-details dt { overflow-wrap:anywhere }
.product-details dd { white-space:pre-wrap; overflow-wrap:anywhere; color:var(--color-text) }
.product-empty { font-size:13px; margin:4px 0 8px }
.product-materials { margin-top:8px }
.material-label { margin:0; font-size:13px; color:var(--color-muted) }
.material-row { flex-wrap:wrap; padding:8px; border:1px solid var(--color-border); border-radius:8px; background:var(--color-background); margin:6px 0 0; gap:8px }
.material-row img { width:48px; height:48px; background:var(--color-panel) }
.material-copy { min-width:0; flex:1; font-size:13px }
.material-copy small { display:block; min-width:0; margin-top:4px }
.material-actions { display:flex; align-items:center; gap:8px; flex-shrink:0 }
.material-actions .button { font-size:12px; white-space:nowrap }
.replace-material { padding:8px; min-height:44px }
.upload-control { position:relative; display:flex; gap:8px; justify-content:space-between; align-items:center; padding:8px 10px; margin-top:6px; background:var(--color-background); border:1px dashed var(--color-border); border-radius:8px }
.upload-control p { font-size:13px; margin:0 }
.upload-control .button { white-space:nowrap }
.generate-button { width:100%; font-weight:600 }
.source-note { font-size:13px; background:var(--color-background); padding:12px; border-radius:8px; margin:0 }
.regeneration-note { margin:0; color:var(--color-muted); font-size:12px; line-height:1.6 }
.history-heading>h2 { margin-right:auto }
.task-history { grid-row:1; padding:0; min-height:320px; display:flex; flex-direction:column; overflow:hidden; background:var(--color-panel) }
.history-heading { display:flex; align-items:baseline; flex-wrap:wrap; gap:4px 12px; padding:14px 20px; border-bottom:1px solid var(--color-border); background:var(--color-panel); flex-shrink:0 }
.history-heading h2 { font-size:15px; font-weight:650; margin:0; min-width:0 }
.results-canvas { padding:20px; min-width:0; flex:1 }
.empty-state { min-height:360px; padding:48px 16px; display:grid; justify-items:center; align-content:center }
.empty-state-icon { display:grid; place-items:center; width:56px; height:56px; border:1px solid var(--color-border); border-radius:16px; background:var(--color-background); color:var(--color-primary); margin-bottom:16px }
.empty-state-icon svg { width:26px; height:26px }
.empty-state h3 { font-size:17px; font-weight:600; margin:0 }
.empty-state p { max-width:24em; margin:8px auto 0; font-size:13px; line-height:1.8 }
.task-unavailable .button { margin-top:20px }
.results-skeleton { padding:18px; border-radius:12px; background:var(--color-panel) }
.skeleton-heading,.skeleton-actions { display:flex; align-items:center; justify-content:space-between; gap:12px }
.skeleton-heading span,.skeleton-actions span,.skeleton-artifact { display:block; background:var(--color-sidebar); border-radius:6px }
.skeleton-heading span:first-child { width:42%; height:18px }
.skeleton-heading span:last-child { width:76px; height:24px }
.skeleton-artifact { width:100%; height:260px; margin:22px 0 16px }
.skeleton-actions { justify-content:flex-start }
.skeleton-actions span { width:72px; height:30px }
.workspace-grid :deep(input:where(:not([class*="el-"])):focus-visible),.workspace-grid :deep(textarea:where(:not([class*="el-"])):focus-visible),.workspace-grid :deep(select:where(:not([class*="el-"])):focus-visible) { outline-width:2px; outline-offset:2px }
@media(hover:hover) { .text-button:hover { color:var(--color-primary); filter:none } }
.product-form>p { margin:0; font-size:13px }
.product-fieldset { border:0; border-top:1px solid var(--color-border); padding:16px 0 0; margin:0; min-width:0 }
.product-fieldset legend { padding:0 12px 0 0; font-weight:600 }
.product-fields { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px }
.product-fields label { font-size:13px }
.product-fields input:where(:not([class*="el-"])),.product-fields textarea:where(:not([class*="el-"])) { font-size:14px }
.wide-field { grid-column:1 / -1 }
.required-label { font-size:12px; color:var(--color-primary) }
.confirmation-product { color:var(--color-text); font-size:17px; font-weight:600 }
.charge-summary { padding:16px 20px; border-radius:8px; background:var(--color-background) }
.charge-summary>span { color:var(--color-muted); font-size:13px }
.charge-amount { margin:4px 0 0; font-size:32px }
.charge-amount small { color:var(--color-primary) }
.snapshot-disclosure { border-top:1px solid var(--color-border); margin-top:20px }
.snapshot-disclosure summary { cursor:pointer; padding:14px 0; min-height:44px; font-size:14px }
@media(min-width:901px) {
  .workspace-grid { height:100%; min-height:0; grid-template-rows:minmax(0,1fr); align-items:stretch }
  .creation-panel { min-height:0 }
  .composer-scroll { flex:1; min-height:0; overflow-y:auto; overscroll-behavior-y:contain; scrollbar-gutter:stable }
  .task-history { min-height:0 }
  .results-canvas { min-height:0; overflow-y:auto; overscroll-behavior-y:contain; scrollbar-gutter:stable }
}
@media(min-width:901px) and (pointer:fine) {
  .workspace-grid :deep(.button:not(.primary)) { min-height:32px; padding:4px 10px; font-size:13px; gap:6px }
  .workspace-grid :deep(.button svg) { width:16px; height:16px }
  .workspace-grid :deep(.button.text-button),.workspace-grid :deep(.button.details-button),.workspace-grid :deep(.button.undo-button) { min-height:28px; padding:2px 0; border:0; background:transparent }
  .composer-tabs :deep(.agent-types .button) { min-height:36px; font-size:14px }
}
@media(min-width:901px) and (max-width:1180px) { .product-details { grid-template-columns:minmax(0,1fr) } }
@media(max-width:900px) { .workspace-grid { gap:16px } .task-history { min-height:320px } }
@media(max-width:700px) { .composer-scroll { padding:12px 16px 16px } .composer-footer { padding:12px 16px } .composer-recovery { padding:16px 16px 0 } .product-details { grid-template-columns:minmax(0,1fr) } }
@media(max-width:700px) { .history-heading { padding:14px 16px } .results-canvas { padding:12px } .empty-state { min-height:280px; padding:32px 12px } .skeleton-artifact { height:220px } }
@media(max-width:400px) { .product-fields { grid-template-columns:minmax(0,1fr) } }
</style>
