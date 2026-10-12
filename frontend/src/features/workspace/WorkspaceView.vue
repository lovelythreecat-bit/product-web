<script setup lang="ts">
import { computed, onScopeDispose, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Schema } from '../../types/api'
import { listAgents, listSpecs, quote as fetchQuote } from '../../api/catalog'
import { createConversation, createProductVersion, getProductVersion } from '../../api/conversations'
import { uploadFile, fileContentUrl } from '../../api/files'
import { submitTaskIntent } from '../../api/tasks'
import { getWork } from '../../api/works'
import { ApiError, createIntent } from '../../api/client'
import { session } from '../auth/session'
import { draftFor, moveDraft, setSourceDraft } from './drafts'
import { useTaskStream } from './useTaskStream'
import AgentSelector from '../../components/AgentSelector.vue'
import SpecForm from '../../components/SpecForm.vue'
import QuotePanel from '../../components/QuotePanel.vue'
import TaskCard from '../../components/TaskCard.vue'
import PromptEditor from './PromptEditor.vue'
import AppDrawer from '../../components/AppDrawer.vue'
import AppDialog from '../../components/AppDialog.vue'

const route = useRoute(), router = useRouter()
const conversationId = computed(() => String(route.params.conversationId || ''))
const draft = computed(() => draftFor(conversationId.value))
const agents = ref<Schema<'AgentVersion'>[]>([]), specs = ref<Schema<'SpecVersion'>[]>([])
const catalogBusy = ref(true)
const agent = computed(() => agents.value.find(a => a.agent_id === draft.value.agentId))
const settings = computed(() => draft.value.agents[draft.value.agentId])
const spec = computed(() => specs.value.find(s => s.spec_id === settings.value?.specId))
const stream = useTaskStream(conversationId)
const { tasks, details, fragments, connectionState } = stream
const error = ref(''), quote = ref<Schema<'Quote'> | null>(null), quoteBusy = ref(false), uploadBusy = ref(false)
const productOpen = ref(false), productSaving = ref(false), productFields = ref<Record<string, string>>({})
const confirmationOpen = ref(false), submitting = ref(false), preparing = ref(false)
const confirmed = computed({ get: () => draft.value.confirmed ?? null, set: value => { draft.value.confirmed = value } })
const pending = computed({ get: () => draft.value.pending ?? null, set: value => { draft.value.pending = value } })
// Pending is authoritative even for drafts saved before an in-flight page exit.
const uncertain = computed(() => !!pending.value && !submitting.value)
let alive = true, quoteVersion = 0, specVersion = 0, quoteTimer: ReturnType<typeof setTimeout> | undefined
const epoch = session.epoch.value
const active = () => alive && epoch === session.epoch.value
onScopeDispose(() => { alive = false; quoteVersion++; specVersion++; clearTimeout(quoteTimer) })
void listAgents().then(value => { if (active()) agents.value = value }).catch(() => { if (active()) error.value = '暂时无法读取可用 Agent。' }).finally(() => { if (active()) catalogBusy.value = false })
watch(() => draft.value.agentId, async id => {
  const stamp = ++specVersion; specs.value = []
  if (!id) return
  draft.value.agents[id] ??= { specId: '', instruction: '', parameters: {} }
  try { const values = await listSpecs(id); if (!active() || stamp !== specVersion) return; specs.value = values; if (!settings.value.specId && values.length === 1) selectSpec(values[0].spec_id) }
  catch { if (active() && stamp === specVersion) error.value = '规格暂时无法读取。' }
}, { immediate: true })
function selectSpec(id: string) {
  settings.value.specId = id
  const selected = specs.value.find(s => s.spec_id === id)
  const previous = settings.value.parameters
  settings.value.parameters = Object.fromEntries(Object.entries(selected?.parameter_schema.fields || {}).flatMap(([name, rule]) => previous[name] !== undefined ? [[name, previous[name]]] : rule.default !== null ? [[name, rule.default]] : []))
}
function parameter(name: string, value: string | number | boolean | undefined) { if (value === undefined) delete settings.value.parameters[name]; else settings.value.parameters[name] = value }
const input = computed<Schema<'InputSnapshot'> | null>(() => draft.value.product && settings.value ? { product_version: draft.value.product.version, product: draft.value.product.product, instruction: settings.value.instruction, parameters: settings.value.parameters, material_versions: draft.value.materials } : null)
const validation = computed(() => {
  if (!agent.value) return '请选择本次创作的 Agent。'
  if (!draft.value.product) return '请先保存商品资料。'
  for (const field of agent.value.input_support.product_required_fields) if (!String(draft.value.product.product[field] ?? '').trim()) return '请补充商品资料：' + field
  if (draft.value.missingMaterials) return '来源素材已不可用，请补传 ' + draft.value.missingMaterials + ' 张商品图片。'
  if (draft.value.materials.length < agent.value.input_support.min_materials) return '请上传至少 ' + agent.value.input_support.min_materials + ' 张商品图片。'
  if (draft.value.materials.length > agent.value.input_support.max_materials) return '商品图片超过当前 Agent 支持数量。'
  if (!spec.value) return '请选择当前生成规格。'
  if (agent.value.input_support.instruction_required && !settings.value.instruction.trim()) return '请填写创作指令。'
  for (const [name, rule] of Object.entries(spec.value.parameter_schema.fields)) {
    const value = settings.value.parameters[name]
    if (value === undefined) { if (rule.required) return '请填写参数：' + name; continue }
    if (rule.choices && !rule.choices.includes(value) || rule.kind === 'integer' && (!Number.isInteger(value) || rule.minimum !== null && Number(value) < rule.minimum || rule.maximum !== null && Number(value) > rule.maximum) || rule.kind === 'string' && rule.max_length !== null && String(value).length > rule.max_length) return '请检查参数：' + name
  }
  const combinations = spec.value.parameter_schema.combinations
  if (combinations.length && !combinations.some(c => Object.keys(c).length === Object.keys(settings.value.parameters).length && Object.entries(c).every(([key, value]) => settings.value.parameters[key] === value))) return '当前参数组合不受支持，请重新选择。'
  return ''
})
const assistRequest = computed<Schema<'AssistRequest'> | null>(() => agent.value && spec.value && draft.value.product ? { agent_id: agent.value.agent_id, agent_version: agent.value.version, spec_id: spec.value.spec_id, spec_version: spec.value.version, original: settings.value.instruction, product: draft.value.product.product, parameters: settings.value.parameters, material_versions: draft.value.materials } : null)
watch(() => JSON.stringify({ input: input.value, spec: spec.value?.spec_id }), () => {
  quote.value = null; quoteBusy.value = false; quoteVersion++; clearTimeout(quoteTimer)
  if (!validation.value) quoteTimer = setTimeout(() => { void refreshQuote() }, 200)
}, { immediate: true })
async function refreshQuote() {
  clearTimeout(quoteTimer)
  quoteTimer = undefined
  const stamp = ++quoteVersion
  if (validation.value || !input.value || !spec.value) return
  quoteBusy.value = true
  try { const value = await fetchQuote({ spec_id: spec.value.spec_id, input: input.value }); if (active() && stamp === quoteVersion) quote.value = value }
  catch (e) { if (active() && stamp === quoteVersion) error.value = e instanceof ApiError ? e.message : '当前报价无法读取。' }
  finally { if (active() && stamp === quoteVersion) quoteBusy.value = false }
}
function editProduct() { productFields.value = Object.fromEntries(Object.entries(draft.value.product?.product || {}).map(([k, v]) => [k, String(v)])); for (const key of new Set(['name', 'description', ...(agent.value?.input_support.product_required_fields || [])])) productFields.value[key] ??= ''; productOpen.value = true }
async function saveProduct() {
  if (!productFields.value.name.trim()) { error.value = '请填写商品名称。'; return }
  productSaving.value = true; const owner = draft.value
  try { const product = await createProductVersion({ product: productFields.value, product_id: owner.product?.product_id }); if (active()) { owner.product = product; productOpen.value = false; error.value = '' } }
  catch (e) { if (active()) error.value = e instanceof ApiError ? e.message : '资料保存失败。' }
  finally { productSaving.value = false }
}
async function upload(event: Event) {
  const control = event.target as HTMLInputElement, file = control.files?.[0]
  if (!file || uploadBusy.value) return
  uploadBusy.value = true; const owner = draft.value
  try { const value = await uploadFile(file); if (active()) { owner.materials.push(value); owner.missingMaterials = Math.max(0, owner.missingMaterials - 1); error.value = '' } }
  catch (e) { if (active()) error.value = e instanceof ApiError ? e.message : '图片上传失败。' }
  finally { uploadBusy.value = false; control.value = '' }
}
async function prepare() {
  if (preparing.value) return
  preparing.value = true
  const owner = draft.value
  try {
  error.value = validation.value
  if (error.value || !input.value || !agent.value || pending.value) return
  if (!quote.value) await refreshQuote()
  if (!active() || draft.value !== owner || !quote.value) return
  const snapshot = JSON.parse(JSON.stringify({ agent_id: agent.value.agent_id, input: input.value, confirmed_quote: quote.value }))
  if (!conversationId.value) { const item = await createConversation({ title: String(owner.product?.product.name || '新会话') }); if (!active() || draft.value !== owner) return; moveDraft('', item.conversation_id); await router.push('/workspace/' + item.conversation_id) }
  confirmed.value = { ...snapshot, conversation_id: conversationId.value }
  confirmationOpen.value = true
  } catch (e) { if (active()) error.value = e instanceof ApiError ? e.message : '无法准备本次创作，请重试。' }
  finally { if (active()) preparing.value = false }
}
async function submit() {
  if (!confirmed.value || submitting.value) return
  pending.value ??= createIntent(confirmed.value)
  const owner = draft.value
  const intent = pending.value
  owner.uncertain = true
  submitting.value = true; error.value = ''
  try {
    const admitted = await submitTaskIntent(intent)
    if (!active() || owner.pending?.key !== intent.key) return
    const taskId = admitted?.task?.task_id
    if (typeof taskId !== 'string' || !taskId.trim()) throw new ApiError('受理回执不完整，请核对原请求。')
    owner.pending = null; owner.uncertain = false
    if (owner === draft.value) confirmationOpen.value = false
    await stream.refreshTask(taskId)
    await session.refreshAccount()
  } catch (e) {
    if (!active() || owner.pending?.key !== intent.key) return
    // Only structured admission rejections prove this intent was not accepted.
    // Proxy/5xx, auth, idempotency conflicts and unreadable success remain uncertain.
    const rejected = e instanceof ApiError && e.status >= 400 && e.status < 500 &&
      e.response?.error.code === e.code && ['QUOTE_STALE', 'INPUT_INVALID', 'SPEC_DISABLED',
        'INSUFFICIENT_CREDITS', 'CAPACITY_INSUFFICIENT', 'FEATURE_NOT_ENABLED', 'MATERIAL_UNAVAILABLE'].includes(e.code ?? '')
    if (rejected && e.code === 'QUOTE_STALE') { owner.pending = null; owner.uncertain = false; owner.agents[owner.agentId].specId = ''; if (owner === draft.value) { confirmationOpen.value = false; quote.value = null; error.value = '报价已更新，请重新选择规格、核对费用并确认。'; const currentSpecs = await listSpecs(owner.agentId); if (active() && owner === draft.value) specs.value = currentSpecs } }
    else if (rejected) { owner.pending = null; owner.uncertain = false; if (owner === draft.value) { confirmationOpen.value = false; error.value = e.message } }
    else { owner.uncertain = true; if (owner === draft.value) error.value = '提交结果尚未确认。请核对原任务或用同一请求重试，不会创建新的意图。' }
  } finally { if (active()) submitting.value = false }
}
async function retry() {
  const owner = draft.value, intent = owner.pending
  if (!intent) return
  await stream.reconnect()
  if (!active() || owner !== draft.value || owner.pending?.key !== intent.key) return
  owner.confirmed = JSON.parse(intent.body)
  confirmationOpen.value = true
}
async function regenerate(work: Schema<'WorkDetail'>) { try { const latest = await getWork(work.work_id); const product = await getProductVersion(latest.source.input.product_version); if (!active()) return; const conversation = await createConversation({ title: '重新创作 · ' + String(product.product.name || '商品') }); if (!active()) return; setSourceDraft(conversation.conversation_id, latest, product); await router.push('/workspace/' + conversation.conversation_id) } catch (e) { if (active()) error.value = e instanceof ApiError ? e.message : '无法读取来源资料。' } }
watch(() => tasks.value.map(t => t.task_id + ':' + t.state_version).join(','), () => { void session.refreshAccount().catch(() => {}) })
watch(conversationId, () => { confirmationOpen.value = false; error.value = '' })
</script>
<template>
  <header class="page-heading"><h1>创作工作台</h1><p>从商品资料出发，让创意成为作品</p></header>
  <div class="workspace-grid">
    <section class="creation-panel panel"><h2>准备本次创作</h2><p v-if="draft.sourceWorkId">重新创作自作品 {{ draft.sourceWorkId }}，将创建独立新任务。</p><p v-if="catalogBusy" role="status">正在读取可用创作能力…</p><fieldset :disabled="catalogBusy || preparing || submitting || !!pending" class="form-stack"><AgentSelector :key="conversationId" v-model="draft.agentId" :agents="agents" /><section class="creation-section"><div class="section-heading"><h3>商品资料</h3><button class="button" type="button" @click="editProduct">编辑商品资料</button></div><p>{{ draft.product?.product.name || '添加商品名称与卖点' }}</p><p v-if="draft.product?.product.description">{{ draft.product.product.description }}</p></section><section class="creation-section"><h3>商品图片</h3><p v-if="draft.missingMaterials" class="field-error" role="alert">来源素材已不可用，请补传 {{ draft.missingMaterials }} 张商品图片。</p><div v-for="(material, index) in draft.materials" :key="material.file_id" class="material-row"><img :src="fileContentUrl(material.file_id)" alt="已上传商品图片" /><small>固定版本 {{ material.version }}</small><button class="button" type="button" @click="draft.materials.splice(index, 1)">移除引用</button></div><label for="material-upload">上传商品图片</label><input id="material-upload" type="file" accept="image/png,image/jpeg,image/webp" :disabled="uploadBusy || !agent || draft.materials.length >= (agent?.input_support.max_materials || 0)" @change="upload" /><p v-if="uploadBusy" role="status">正在保存图片…</p></section><PromptEditor v-if="settings" :key="conversationId + draft.agentId" v-model="settings.instruction" :request="assistRequest" /><details v-if="settings" class="creation-section" open><summary>生成设置</summary><SpecForm :specs="specs" :spec-id="settings.specId" :parameters="settings.parameters" @spec="selectSpec" @parameter="parameter" /></details><QuotePanel :quote="quote" :loading="quoteBusy" /><p v-if="validation" class="field-hint">{{ validation }}</p><button class="button primary" type="button" :disabled="quoteBusy || uploadBusy || productSaving" @click="prepare">确认费用并生成</button></fieldset><p v-if="error" class="field-error" role="alert">{{ error }}</p><button v-if="uncertain" class="button" type="button" @click="retry">核对并重试原请求</button></section>
    <section class="task-history" aria-label="当前会话任务"><div class="section-heading"><h2>会话记录</h2><button v-if="conversationId" class="button" type="button" @click="stream.reconnect">刷新原任务</button></div><p v-if="connectionState === 'recovering'" role="status">正在核对原任务，生成会继续进行。</p><div v-if="!tasks.length" class="panel empty-state"><h2>准备好，就开始创作</h2><p>保存商品资料，选择 Agent 与规格。确认费用后，任务会保留在当前会话。</p></div><TaskCard v-for="task in tasks" :key="task.task_id" :detail="details[task.task_id]" :agent="agents.find(a => a.agent_id === details[task.task_id].agent_id)" :fragment="fragments[task.task_id]" @regenerate="regenerate" /></section>
  </div>
  <AppDrawer v-model:open="productOpen" title="编辑商品资料" purpose="edit"><form id="product-form" class="form-stack" @submit.prevent="saveProduct"><div v-for="(_, field) in productFields" :key="field"><label :for="'product-' + field">{{ field === 'name' ? '商品名称' : field === 'description' ? '商品卖点与说明' : field }}</label><input :id="'product-' + field" v-model="productFields[field]" :data-initial-focus="field === 'name' ? '' : undefined" /></div><p v-if="error" class="field-error" role="alert">{{ error }}</p></form><template #actions><button class="button primary" type="submit" form="product-form" :disabled="productSaving">保存商品资料</button></template></AppDrawer>
  <AppDialog v-model:open="confirmationOpen" title="确认本次创作" purpose="charge"><template v-if="confirmed"><p class="charge-amount">{{ confirmed.confirmed_quote.credits }} 积分</p><p>确认后冻结上述积分；完整成功后消费，确定失败后释放。</p><dl class="detail-list"><dt>Agent</dt><dd>{{ agents.find(a => a.agent_id === confirmed!.agent_id)?.name }} · {{ confirmed.confirmed_quote.agent_version }}</dd><dt>规格与报价版本</dt><dd>{{ confirmed.confirmed_quote.spec_id }} · {{ confirmed.confirmed_quote.spec_version }} / {{ confirmed.confirmed_quote.price_version }}</dd><dt>完整输入快照</dt><dd><pre>{{ JSON.stringify(confirmed.input, null, 2) }}</pre></dd></dl><p v-if="error" class="field-error" role="alert">{{ error }}</p></template><template #actions><button class="button primary" type="button" :disabled="submitting" @click="submit">{{ submitting ? '正在提交…' : '同意并冻结积分' }}</button></template></AppDialog>
</template>
