import { computed, onScopeDispose, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import type { Schema } from '../../types/api'
import * as api from '../../api/quickGeneration'
import { listAgents, quote } from '../../api/catalog'
import { getProductVersion } from '../../api/conversations'
import { fileContentUrl, uploadFile } from '../../api/files'
import { getWork } from '../../api/works'
import { ApiError } from '../../api/client'
import { session } from '../auth/session'
import { validateTextParameters } from '../workspace/textParameters'
import { quickGenerationRevision } from './activity'
import { MAX_PRODUCT_REFERENCES } from '../workspace/materialLimits'
export const outputs: { value: api.ImageOutput; label: string; count: number; description: string }[] = [
  { value: 'main_image', label: '商品主图', count: 1, description: '突出商品主体，用于商品首屏展示。' },
  { value: 'detail_page', label: '详情图', count: 3, description: '呈现商品外观、结构与使用场景。' },
  { value: 'long_image', label: '商品长图', count: 1, description: '将商品信息串联成一张完整长图。' },
]
export const platforms = [['amazon', 'Amazon'], ['taobao', '淘宝'], ['tmall', '天猫'], ['jd', '京东'], ['pinduoduo', '拼多多'], ['shopee', 'Shopee'], ['lazada', 'Lazada'], ['shein', 'SHEIN'], ['temu', 'Temu']]
export const copyTypeChoices = ['宣传文案', '商品标题', '卖点描述', '详情介绍', '社交平台文案', '直播口播', '营销策略']
export const emptyDraft = (): api.QuickDraft => ({ product_version: null, material_versions: [], copy_parameters: { platform: '淘宝', tone: '自然' }, copy_types: [...copyTypeChoices], copy_texts: {}, copy_instruction: '', copy_text: '', image_platform: '', image_outputs: [], image_instruction: '', video_first_frame_file_id: '', video_instruction: '' })
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value))
export function useQuickGeneration() {
  const route = useRoute(), router = useRouter()
  const run = ref<api.QuickView | null>(null), draft = ref<api.QuickDraft>(emptyDraft())
  const product = ref<Schema<'ProductVersionView'> | null>(null), agents = ref<Schema<'AgentVersion'>[]>([])
  const loading = ref(true), busy = ref(false), error = ref(''), feedback = ref(''), conflict = ref(false)
  const productOpen = ref(false), requirementsOpen = ref(false), chargeOpen = ref(false), uncertain = ref(false)
  const estimated = ref<number | null>(null), estimateBusy = ref(false), imageQuotes = ref<Record<string, number>>({})
  const uploadControl = ref<HTMLInputElement>(), uploading = ref(false)
  let alive = true, stamp = 0, polling = false, baseline = '', mutationRevision = 0, exiting = false, timer: ReturnType<typeof setTimeout> | undefined
  let localValidation = ''
  let progressReadError = ''
  let creationId = ''
  let accountNeedsRefresh = false
  let accountReading = false
  let submissionPending = false, submissionRevision = 0
  let submittingBatchId = ''
  const taskStates = (value: api.QuickView) => JSON.stringify(Object.values(value.tasks).map(detail => [detail.task.task_id, detail.task.state_version, detail.task.settlement_state]))
  const epoch = session.epoch.value
  const active = () => alive && session.epoch.value === epoch
  function refreshBalance() {
    if (!accountNeedsRefresh || accountReading || !active()) return
    const states = run.value ? taskStates(run.value) : ''
    accountReading = true
    void session.refreshAccount().then(() => {
      if (active() && run.value && states === taskStates(run.value)) accountNeedsRefresh = false
    }).catch(() => { /* Retry with a later progress poll. */ }).finally(() => { accountReading = false })
  }
  const viewedStep = ref<number | null>(null)
  const progressStep = computed(() => run.value?.state.step || 1)
  const readOnly = computed(() => progressStep.value === 5)
  const step = computed(() => viewedStep.value ?? progressStep.value)
  const dirty = computed(() => !!run.value && !readOnly.value && JSON.stringify(draft.value) !== baseline)
  const batches = computed(() => run.value?.state.batches || [])
  const currentBatch = (kind: api.QuickKind) => batches.value.find(batch => batch.id === run.value?.state.current[kind])
  const currentItems = (kind: api.QuickKind) => (currentBatch(kind)?.items || []).map(item => ({ ...item, detail: item.task_id ? run.value?.tasks[item.task_id] : undefined }))
  const kind = computed<api.QuickKind>(() => step.value < 3 ? 'copy' : step.value === 3 ? 'image' : 'video')
  const current = computed(() => currentItems(kind.value))
  const copyEntries = computed(() => currentItems('copy').map(item => ({
    key: String(item.request?.input.parameters.copy_type || item.label), label: item.label, free_regenerations_used: item.free_regenerations_used || 0,
  })))
  const multipleCopies = computed(() => copyEntries.value.length > 1)
  const copyReady = computed(() => multipleCopies.value ? copyEntries.value.every(item => draft.value.copy_texts[item.key]?.trim()) : !!draft.value.copy_text.trim())
  function updateCopy(key: string, text: string) {
    if (readOnly.value) return
    draft.value.copy_texts[key] = text
    draft.value.copy_text = copyEntries.value.map(item => '【' + item.label + '】\n' + (draft.value.copy_texts[item.key] || '').trim()).join('\n\n')
  }
  const complete = computed(() => current.value.length > 0 && current.value.every(item => item.detail?.task.state === 'SUCCEEDED' && item.detail.task.settlement_state === 'CONSUMED'))
  const stageStatus = computed(() => {
    if (readOnly.value) return ''
    if (!current.value.length) return ''
    const tasks = current.value.map(item => item.detail?.task)
    const label = kind.value === 'copy' ? '文案' : kind.value === 'image' ? '图片' : '视频'
    if (complete.value) return label + '已生成并保存，请查看成果后确认下一步。'
    if (tasks.some(task => task?.state === 'INVESTIGATING' && task.investigation_reason === 'UPSTREAM_NEEDS_INPUT') && kind.value === 'image') return '部分图片任务已停止，等待补充资料。可在对应任务中使用原资料重试。'
    if (tasks.some(task => task?.state === 'FAILED')) return label + '生成失败，可在下方任务中选择重试或释放积分。'
    if (tasks.some(task => task?.state === 'MANUALLY_CLOSED')) return '本阶段任务已关闭。请查看任务记录，需要继续时重新确认费用生成。'
    if (tasks.some(task => ['INVESTIGATING', 'SAVE_RECOVERY'].includes(task?.state || ''))) return '任务正在核查或恢复原结果，请查看下方任务状态。请勿重复提交。'
    if (tasks.every(task => !task || ['SUBMITTED', 'QUEUED'].includes(task.state))) return label + '任务已提交，正在后台排队。可以保存并退出，稍后继续。'
    return label + '正在后台生成，进度会自动更新。可以保存并退出，稍后继续。'
  })
  const locked = computed(() => !!run.value && Object.values(run.value.tasks).some(detail => !['SUCCEEDED', 'FAILED', 'MANUALLY_CLOSED'].includes(detail.task.state) || detail.task.state === 'FAILED' && detail.task.settlement_state === 'FROZEN'))
  const pendingBatch = computed(() => batches.value.find(batch => batch.id === run.value?.state.pending_batch))
  const newCharges = computed(() => pendingBatch.value?.items.filter(item => !item.task_id) || [])
  const chargeFor = (item: NonNullable<api.QuickView['state']['batches']>[number]['items'][number]) => item.free_regeneration ? 0 : item.request.confirmed_quote.credits
  const total = computed(() => newCharges.value.reduce((sum, item) => sum + chargeFor(item), 0))
  const imageCount = computed(() => outputs.filter(output => draft.value.image_outputs.includes(output.value)).reduce((sum, output) => sum + output.count, 0))
  const requiredFields = computed(() => agents.value.find(agent => agent.kind === 'copy' && agent.enabled)?.input_support.product_required_fields || [])
  const materials = computed(() => draft.value.material_versions)
  type Frame = { file_id: string; version: string; label: string }
  const generatedFrames = ref<Frame[]>([]), framesLoading = ref(false), framesError = ref('')
  const imageSourceKey = computed(() => {
    if (!run.value?.state.confirmed_images || run.value.state.confirmed_images !== run.value.state.current.image) return ''
    const items = currentItems('image')
    if (!items.length || items.some(item => item.detail?.task.state !== 'SUCCEEDED' || item.detail.task.settlement_state !== 'CONSUMED')) return ''
    return JSON.stringify([run.value.run_id, run.value.state.confirmed_images, items.map(item => [item.detail!.task.task_id, item.detail!.task.work_ids])])
  })
  const frameCandidates = computed<Frame[]>(() => [...materials.value.map((item, index) => ({ ...item, label: '商品参考图 ' + (index + 1) })), ...generatedFrames.value])
  const videoMaterials = computed(() => {
    const frame = frameCandidates.value.find(item => item.file_id === draft.value.video_first_frame_file_id)
    return frame ? [{ file_id: frame.file_id, version: frame.version }] : []
  })
  async function readFrames() {
    const key = imageSourceKey.value
    if (!key) return
    framesLoading.value = true; framesError.value = ''
    try {
      const groups = await Promise.all(currentItems('image').map(async item => {
        const works = await Promise.all(item.detail!.task.work_ids.map(getWork))
        return works.flatMap(work => work.kind === 'image' ? work.items.filter(result => result.media_type.startsWith('image/') && result.file_version).map((result, index) => ({ file_id: result.file_id, version: result.file_version, label: item.label + ' · 成果 ' + (index + 1) })) : [])
      }))
      if (active() && key === imageSourceKey.value) generatedFrames.value = [...new Map(groups.flat().map(frame => [frame.file_id, frame])).values()]
    } catch { if (active() && key === imageSourceKey.value) framesError.value = '生成图片暂时无法读取，请重试。' }
    finally { if (active() && key === imageSourceKey.value) framesLoading.value = false }
  }
  watch(imageSourceKey, () => { generatedFrames.value = []; framesLoading.value = false; framesError.value = ''; void readFrames() }, { flush: 'sync' })
  function apply(value: api.QuickView, replaceDraft = true) {
    if (String(route.params.runId || '') !== value.run_id) return
    const changed = run.value?.run_id !== value.run_id || run.value?.version !== value.version
    run.value = value
    if (changed) quickGenerationRevision.value++
    if (replaceDraft) { draft.value = { ...emptyDraft(), ...clone(value.state.draft) }; baseline = JSON.stringify(draft.value) }
  }
  async function readProduct() {
    const version = draft.value.product_version
    if (!version) { product.value = null; return }
    if (product.value?.version === version) return
    const value = await getProductVersion(version)
    if (active() && draft.value.product_version === version) product.value = value
  }
  async function refresh(replaceDraft = false) {
    if (!run.value || polling || busy.value && !submissionPending) return
    polling = true
    const id = run.value.run_id, revision = mutationRevision
    try {
      const value = await api.getQuickRun(id)
      if (!active() || run.value?.run_id !== id || revision !== mutationRevision || value.version < run.value.version) return
      if (dirty.value && value.version !== run.value.version && !replaceDraft) { conflict.value = true; error.value = '进度已在其他窗口更新。请先保留需要的文字，再重新读取进度。'; return }
      if (progressReadError && error.value === progressReadError) error.value = ''
      progressReadError = ''
      accountNeedsRefresh ||= taskStates(value) !== taskStates(run.value)
      apply(value, replaceDraft || !dirty.value)
      if (submissionPending && acceptedBatch(value, submittingBatchId)) finishSubmission(value, submittingBatchId)
      if (!value.state.pending_batch) { uncertain.value = false; chargeOpen.value = false }
      if (replaceDraft) { conflict.value = false; error.value = '' }
      await readProduct(); await fillCopy()
      refreshBalance()
    } catch (cause) { if (active() && run.value?.run_id === id && revision === mutationRevision) error.value = progressReadError = message(cause) }
    finally { polling = false }
  }
  async function fillCopy() {
    if (!run.value || step.value !== 2) return
    const items = currentItems('copy'), runId = run.value.run_id, batchId = run.value.state.current.copy
    if (items.length > 1) {
      await Promise.all(items.map(async item => {
        const key = String(item.request.input.parameters.copy_type || item.label)
        if (Object.hasOwn(draft.value.copy_texts, key) || item.detail?.task.state !== 'SUCCEEDED' || item.detail.task.settlement_state !== 'CONSUMED') return
        const works = await Promise.all(item.detail.task.work_ids.map(getWork))
        if (!active() || run.value?.run_id !== runId || run.value.state.current.copy !== batchId || Object.hasOwn(draft.value.copy_texts, key)) return
        const wasDirty = dirty.value
        updateCopy(key, works.flatMap(work => work.items.map(item => item.text || '')).join('\n\n'))
        // Generated results can be read while tasks lock the server draft.
        // They must not force a forbidden save when navigating away.
        if (!wasDirty && locked.value) baseline = JSON.stringify(draft.value)
      }))
    } else {
      const item = items[0]?.detail
      if (draft.value.copy_text || item?.task.state !== 'SUCCEEDED' || !item.task.work_ids.length) return
      const works = await Promise.all(item.task.work_ids.map(getWork))
      if (!active() || run.value?.run_id !== runId || run.value.state.current.copy !== batchId || draft.value.copy_text) return
      const wasDirty = dirty.value
      draft.value.copy_text = works.flatMap(work => work.items.map(item => item.text || '')).join('\n\n')
      if (!wasDirty && locked.value) baseline = JSON.stringify(draft.value)
    }
  }
  function message(cause: unknown) { return cause instanceof Error ? cause.message : '操作暂时无法完成，请重试。' }
  async function save() {
    if (readOnly.value) return
    if (!run.value || conflict.value) throw new Error('请重新读取最新进度后继续。')
    if (dirty.value) {
      mutationRevision++
      const value = await api.saveQuickRun(run.value.run_id, run.value.version, clone(draft.value))
      if (!active()) return
      apply(value)
    }
  }
  async function perform(operation: () => Promise<void>) {
    if (busy.value || conflict.value || !active()) return
    busy.value = true; error.value = ''; feedback.value = ''
    mutationRevision++
    try { await operation() }
    catch (cause) { if (active()) error.value = message(cause) }
    finally { if (active()) busy.value = false }
  }
  async function initialize() {
    const revision = ++stamp
    loading.value = true; run.value = null; error.value = ''; baseline = ''; draft.value = emptyDraft(); product.value = null
    submissionRevision++; submissionPending = false; submittingBatchId = ''; busy.value = false
    uncertain.value = false; conflict.value = false; productOpen.value = false; chargeOpen.value = false; requirementsOpen.value = false; viewedStep.value = null
    try {
      const runId = String(route.params.runId || '')
      if (!runId) {
        const saved = await api.listQuickRuns()
        if (!active() || revision !== stamp) return
        let id = saved[0]?.run_id
        if (!id) {
          creationId ||= crypto.randomUUID()
          const created = await api.createQuickRun(creationId)
          if (!active() || revision !== stamp) return
          id = created.run_id
        }
        await router.replace('/workspace/quick/' + encodeURIComponent(id))
        return
      }
      const values = await Promise.all([api.getQuickRun(runId), listAgents()])
      if (!active() || revision !== stamp) return
      apply(values[0]); agents.value = values[1]
      uncertain.value = !!pendingBatch.value
      await readProduct(); await fillCopy()
    } catch (cause) { if (active() && revision === stamp) error.value = message(cause) }
    finally { if (active() && revision === stamp) loading.value = false }
  }
  const validation = (target: api.QuickKind) => {
    if (!product.value) return '请先填写并保存商品资料。'
    if (materials.value.length > MAX_PRODUCT_REFERENCES) return `商品参考图最多支持 ${MAX_PRODUCT_REFERENCES} 张，请移除多余引用后生成。`
    const agent = agents.value.find(agent => agent.kind === target && agent.enabled)
    if (target === 'copy') { const error = validateTextParameters(Object.fromEntries(Object.entries(draft.value.copy_parameters).filter(([key]) => key !== 'audience'))); if (error) return error }
    if (target === 'image') {
      if (!draft.value.image_platform) return '请选择目标平台。'
      if (!draft.value.image_outputs.length) return '请选择至少一种图片内容。'
    }
    if (target === 'video' && !videoMaterials.value.length) return '请从商品参考图或本次生成图片中选择视频首帧。'
    if (target !== 'copy' && !product.value.product.category) return '请补充商品分类。'
    // The server selects copy materials using the actual default model's image
    // capability. Workflow references may be reserved for later media stages.
    const selectedMaterials = target === 'video' ? videoMaterials.value : materials.value
    if (target !== 'copy' && agent && selectedMaterials.length < agent.input_support.min_materials) return '请上传至少 ' + agent.input_support.min_materials + ' 张商品图片。'
    if (target !== 'copy' && agent && selectedMaterials.length > agent.input_support.max_materials) return '商品图片超过当前创作类型支持数量，请调整。'
    return ''
  }
  async function prepare(target: api.QuickKind = kind.value, subset?: api.ImageOutput[], itemIndex?: number) {
    if (readOnly.value) return
    const invalid = validation(target)
    if (invalid) { localValidation = invalid; error.value = invalid; return }
    await perform(async () => {
      // Removed editor fields must not silently override product facts in a new batch.
      if (!pendingBatch.value) {
        draft.value[target === 'copy' ? 'copy_instruction' : target === 'image' ? 'image_instruction' : 'video_instruction'] = ''
        if (target === 'copy') {
          const { audience: _audience, max_chars: _max, extra_instructions: _extra, ...parameters } = draft.value.copy_parameters
          draft.value.copy_parameters = parameters
        }
      }
      await save(); if (!active() || !run.value) return
      const value = itemIndex === undefined
        ? await api.prepareQuickRun(run.value.run_id, run.value.version, target, subset)
        : await api.prepareQuickRun(run.value.run_id, run.value.version, target, subset, itemIndex)
      if (active()) { apply(value); chargeOpen.value = true; uncertain.value = false }
    })
  }
  const acceptedBatch = (value: api.QuickView, batchId: string) => {
    const batch = value?.state?.batches?.find(batch => batch.id === batchId)
    return !!(batch?.submitted && batch.items.length && batch.items.every(item => item.task_id))
  }
  function finishSubmission(value: api.QuickView, batchId: string) {
    if (!active() || value.run_id !== run.value?.run_id || !acceptedBatch(value, batchId)) return
    submissionRevision++; submissionPending = false; submittingBatchId = ''
    viewedStep.value = null; apply(value); uncertain.value = false; chargeOpen.value = false; requirementsOpen.value = false; busy.value = false
    feedback.value = '任务已受理，生成进度会自动更新。'
    accountNeedsRefresh = true; refreshBalance()
    void fillCopy().catch(cause => { if (active() && run.value?.run_id === value.run_id) error.value = message(cause) })
  }
  async function submit() {
    if (readOnly.value || busy.value || conflict.value || !active()) return
    if (!pendingBatch.value || !run.value) return
    const id = run.value.run_id, batchId = pendingBatch.value.id
    const revision = ++submissionRevision
    mutationRevision++; busy.value = true; error.value = ''; feedback.value = ''
    submissionPending = true; submittingBatchId = batchId; uncertain.value = true
      try {
        const value = await api.submitQuickBatch(id, batchId)
        if (!active() || revision !== submissionRevision || run.value?.run_id !== id) return
        if (value?.run_id !== id || !acceptedBatch(value, batchId)) throw new ApiError('受理回执尚未完整确认。')
        finishSubmission(value, batchId)
      } catch (cause) {
        if (!active() || revision !== submissionRevision || run.value?.run_id !== id) return
        // Only a structured admission rejection proves the whole transaction rolled back.
        if (cause instanceof ApiError && cause.response && ['QUOTE_STALE', 'INPUT_INVALID', 'INSUFFICIENT_CREDITS', 'FEATURE_NOT_ENABLED', 'FORBIDDEN', 'MATERIAL_UNAVAILABLE', 'CAPACITY_INSUFFICIENT', 'SPEC_DISABLED', 'RATE_LIMITED'].includes(cause.code || '') && cause.status >= 400 && cause.status < 500) {
          uncertain.value = false; chargeOpen.value = false
          error.value = '任务未受理：' + (cause.code === 'QUOTE_STALE' ? '报价已更新，请重新确认费用。' : cause.message) + '此次未创建新任务，也未冻结积分。'
          return
        }
        error.value = '提交结果尚未确认，请核对原请求；进度和原收费请求已保留。'
      } finally {
        if (active() && revision === submissionRevision) { busy.value = false; submissionPending = false; submittingBatchId = '' }
      }
  }
  async function advance(action: Schema<'QuickAdvance'>['action']) {
    if (action === 'back') { await goToStep(step.value - 1); return }
    if (readOnly.value) return
    await perform(async () => {
      await save(); if (!active() || !run.value) return
      const value = await api.advanceQuickRun(run.value.run_id, run.value.version, action)
      if (active()) { viewedStep.value = action === 'confirm_copy' ? 2 : null; apply(value); requirementsOpen.value = false; await fillCopy() }
    })
  }
  function canGoToStep(target: number) {
    return Number.isInteger(target) && target >= 1 && target <= progressStep.value
  }
  async function goToStep(target: number) {
    if (!canGoToStep(target) || target === step.value || uploading.value || uncertain.value || chargeOpen.value) return
    await perform(async () => {
      await save()
      if (!active() || !canGoToStep(target)) return
      viewedStep.value = target; requirementsOpen.value = false
      await fillCopy()
    })
  }
  async function closeCharge(open: boolean) {
    if (readOnly.value) { chargeOpen.value = false; return }
    chargeOpen.value = open
    if (open || busy.value || !run.value || !pendingBatch.value) return
    const id = run.value.run_id, batchId = pendingBatch.value.id
    await perform(async () => {
      uncertain.value = true
      const value = await api.cancelQuickBatch(id, batchId)
      if (!active()) return
      apply(value); uncertain.value = !!value.state.pending_batch
    })
  }
  async function saveExit() {
    await perform(async () => { await save(); if (active()) { exiting = true; try { await router.push('/works') } finally { exiting = false } } })
  }
  async function savedProduct(value: Schema<'ProductVersionView'>) {
    if (readOnly.value) return
    product.value = value; draft.value.product_version = value.version
    await perform(save)
    if (error.value) throw new Error(error.value)
  }
  async function upload(event: Event | File) {
    const control = event instanceof File ? null : event.target as HTMLInputElement
    const file = event instanceof File ? event : control?.files?.[0]
    if (!file || readOnly.value || uploading.value || locked.value || busy.value || uncertain.value || conflict.value) return false
    if (materials.value.length >= MAX_PRODUCT_REFERENCES) { error.value = `最多上传 ${MAX_PRODUCT_REFERENCES} 张商品图片。`; return false }
    uploading.value = true
    try { const material = await uploadFile(file); if (active()) { draft.value.material_versions.push({ file_id: material.file_id, version: material.version }); await perform(save); return !error.value } return false }
    catch (cause) { if (active()) error.value = message(cause); return false }
    finally { uploading.value = false; if (control) control.value = '' }
  }
  async function removeMaterial(index: number) {
    if (readOnly.value || uploading.value || locked.value || busy.value || uncertain.value || conflict.value) return
    draft.value.material_versions.splice(index, 1)
    if (!frameCandidates.value.some(m => m.file_id === draft.value.video_first_frame_file_id)) draft.value.video_first_frame_file_id = ''
    await perform(save)
  }
  async function copy(text = draft.value.copy_text) {
    try { await navigator.clipboard.writeText(text); feedback.value = '已复制完整文案' }
    catch { error.value = '无法自动复制，请选择文案复制。' }
  }
  let quoteRevision = 0
  async function estimate() {
    const revision = ++quoteRevision
    estimated.value = null
    imageQuotes.value = {}
    estimateBusy.value = false
    if (readOnly.value) return
    const target = requirementsOpen.value ? 'image' : kind.value
    const agent = agents.value.find(a => a.kind === target && a.enabled)
    if (!agent || !product.value || !run.value) return
    if (target === 'image' && !draft.value.image_platform || target === 'video' && !draft.value.video_first_frame_file_id) return
    estimateBusy.value = true
    const parameters = target === 'copy' ? Object.fromEntries(Object.entries(draft.value.copy_parameters).filter(([key]) => !['audience', 'max_chars', 'extra_instructions'].includes(key))) : target === 'image' ? { platform: draft.value.image_platform } : { first_frame_file_id: draft.value.video_first_frame_file_id }
    const confirmedCopy = run.value.state.confirmed_copy || ''
    const confirmedTypes = copyEntries.value.map(entry => entry.key)
    const detailCopy = confirmedCopy && confirmedTypes.includes('详情介绍')
      ? (confirmedTypes.length === 1 ? confirmedCopy.trim() : draft.value.copy_texts['详情介绍']?.trim() || '') : ''
    const instruction = target === 'copy' ? '' : target === 'image'
      ? detailCopy
      : draft.value.video_instruction + '\n\n已由用户确认的营销文案（仅作为创作输入，商品事实以商品资料和参考图为准）：\n' + confirmedCopy
    const selections = target === 'image' ? draft.value.image_outputs : target === 'copy' ? (draft.value.copy_types.length ? draft.value.copy_types : [undefined]) : [undefined]
    try {
      const values = await Promise.all(selections.map(selection => quote({ agent_id: agent.agent_id, input: { product_version: product.value!.version, product: product.value!.product, material_versions: target === 'video' ? videoMaterials.value : materials.value, instruction, parameters: { ...parameters, ...(selection ? { [target === 'image' ? 'output_type' : 'copy_type']: selection } : {}) } } })))
      if (active() && revision === quoteRevision) {
        estimated.value = values.reduce((sum, value) => sum + value.credits, 0)
        if (target === 'image') imageQuotes.value = Object.fromEntries(selections.map((selection, index) => [selection!, values[index]!.credits]))
      }
    }
    catch { /* The confirmation action surfaces exact server validation. */ }
    finally { if (active() && revision === quoteRevision) estimateBusy.value = false }
  }
  watch(() => JSON.stringify([draft.value, kind.value, requirementsOpen.value, product.value?.version, agents.value.length, videoMaterials.value]), () => { if (localValidation && error.value === localValidation) { error.value = ''; localValidation = '' }; quoteRevision++; estimated.value = null; imageQuotes.value = {}; estimateBusy.value = false; clearTimeout(timer); timer = setTimeout(() => { void estimate() }, 250) }, { flush: 'sync' })
  watch(() => route.params.runId, () => { void initialize() }, { immediate: true })
  const interval = setInterval(() => { if (run.value && !document.hidden && !conflict.value) void refresh() }, 3000)
  function beforeUnload(event: BeforeUnloadEvent) { if (dirty.value) event.preventDefault() }
  window.addEventListener('beforeunload', beforeUnload)
  async function saveBeforeNavigation() {
    if (!exiting && (busy.value || uploading.value)) { error.value = '当前操作正在处理，请稍后切换。'; return false }
    if (dirty.value) { try { await save() } catch (cause) { error.value = message(cause); return false } }
  }
  onBeforeRouteLeave(saveBeforeNavigation)
  onBeforeRouteUpdate(saveBeforeNavigation)
  onScopeDispose(() => { alive = false; stamp++; quoteRevision++; clearInterval(interval); clearTimeout(timer); window.removeEventListener('beforeunload', beforeUnload) })
  return { run, draft, product, agents, step, progressStep, readOnly, canGoToStep, goToStep, kind, current, currentItems, currentBatch, copyEntries, multipleCopies, copyReady, updateCopy, complete, stageStatus, locked, dirty, loading, busy, error, feedback, conflict, productOpen, requirementsOpen, chargeOpen, uncertain, pendingBatch, newCharges, chargeFor, total, imageCount, estimated, imageQuotes, estimateBusy, requiredFields, materials, frameCandidates, videoMaterials, framesLoading, framesError, readFrames, uploadControl, uploading, refresh, initialize, prepare, submit, closeCharge, advance, saveExit, savedProduct, upload, removeMaterial, copy, fileContentUrl }
}
