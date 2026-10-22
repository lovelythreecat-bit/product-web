<script setup lang="ts">
import { ElTable, ElTableColumn } from 'element-plus/es/components/table/index'
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import { onMounted, ref } from 'vue'
import * as api from '../../api/admin'
import type { Schema } from '../../types/api'
import AppDrawer from '../../components/AppDrawer.vue'
import { useAdminRequest } from './shared'

const { busy, error, run } = useAdminRequest()
const emit = defineEmits<{ 'default-saved': [] }>()
const models = ref<Schema<'TextModelView'>[]>([])
const defaultModel = ref<Schema<'TextDefaultModelView'> | null>(null)
const defaultOpen = ref(false), defaultConflict = ref(false)
const selectedDefault = ref<Schema<'TextModelView'> | null>(null)
const nextCursor = ref<string | null>(null), open = ref(false), notice = ref('')
const editing = ref<{ id: string; revision: number } | null>(null)
const conflict = ref(false)
const reasoningEfforts = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'] as const
type ReasoningChoice = typeof reasoningEfforts[number] | ''
function empty() {
  return { name: '', provider: 'openai_chat' as const, base_url: '', model: '', api_key: '', supports_images: false, timeout_seconds: 60, temperature: null as number | null, max_tokens: null as number | null, reasoning_effort: '' as ReasoningChoice, enabled: true }
}
const draft = ref(empty())
function load(more = false) {
  return run(() => Promise.all([api.listTextModels(more ? nextCursor.value ?? undefined : undefined), api.getTextDefaultModel()]), ([result, preference]) => {
    models.value = more ? [...models.value, ...result.items] : result.items
    nextCursor.value = result.next_cursor ?? null
    defaultModel.value = preference
  })
}
function chooseDefault(row: Schema<'TextModelView'>) {
  selectedDefault.value = row; defaultConflict.value = false
  error.value = ''; defaultOpen.value = true
}
async function reloadDefault() {
  await run(api.getTextDefaultModel, value => {defaultModel.value = value; defaultConflict.value = false})
}
async function saveDefault() {
  if (!selectedDefault.value || !defaultModel.value || defaultConflict.value) return
  await run(async () => {
    try {
      return await api.saveTextDefaultModel({model_config_id:selectedDefault.value!.id,
        expected_revision:defaultModel.value!.revision,
        expected_connection_revision:defaultModel.value!.connection_revision})
    } catch(e) {
      if(e instanceof Error && 'status' in e && e.status === 409) defaultConflict.value = true
      throw e
    }
  }, value => {
    defaultModel.value = value; defaultOpen.value = false
    notice.value = '默认文本模型已更新，新提交的文案任务将使用此模型。'
    emit('default-saved')
  })
}
function edit(row?: Schema<'TextModelView'>) {
  editing.value = row ? { id: row.id, revision: row.revision } : null
  draft.value = row ? { name: row.name, provider: 'openai_chat', base_url: row.base_url, model: row.model, api_key: '', supports_images: row.supports_images, timeout_seconds: row.timeout_seconds, temperature: row.temperature, max_tokens: row.max_tokens, reasoning_effort: row.reasoning_effort ?? '', enabled: row.enabled } : empty()
  error.value = ''; conflict.value = false; open.value = true
}
async function save() {
  if (conflict.value) return
  const { api_key, enabled, reasoning_effort, ...otherFields } = draft.value
  const fields = { ...otherFields, reasoning_effort: reasoning_effort || null }
  const current = editing.value
  const config = { ...fields, ...(api_key ? { api_key } : {}) }
  const ok = await run(async () => {
    try {
      return current
        ? await api.updateTextModel(current.id, { expected_revision: current.revision, config: { ...config, enabled } })
        : await api.createTextModel({ config: { ...fields, api_key } })
    } catch (e) {
      if (e instanceof Error && 'status' in e && e.status === 409) conflict.value = true
      throw e
    }
  }, result => {
    models.value = [result, ...models.value.filter(row => row.id !== result.id)]
    draft.value.api_key = ''; open.value = false
    notice.value = '模型配置已保存。'
  })
  return ok
}
async function reloadConflict() {
  // Reopen the current server value explicitly instead of silently overwriting a newer revision.
  const selected = editing.value?.id
  if (selected) await run(() => api.getTextModel(selected), latest => {
    models.value = models.value.map(row => row.id === latest.id ? latest : row)
    edit(latest)
  })
}
function optionalNumber(event: Event, field: 'temperature' | 'max_tokens') {
  const value = (event.target as HTMLInputElement).value
  draft.value[field] = value === '' ? null : Number(value)
}
onMounted(() => load())
const RowColumn = ElTableColumn<Schema<'TextModelView'>>
</script>

<template>
  <section class="panel">
    <div class="section-heading"><h2>文本模型配置</h2><div class="button-row"><UiButton class="button" :disabled="busy" @click="load()">刷新模型配置</UiButton><UiButton class="button primary" :disabled="busy" @click="edit()">新增模型配置</UiButton></div></div>
    <p v-if="error && !open && !defaultOpen" class="field-error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="defaultModel && !defaultModel.model_config_id" class="field-hint">请指定一个默认模型，供工作台文案生成使用。</p>
    <p v-if="defaultModel?.model_config_id && defaultModel.generation_policy_configured === false" class="field-hint">默认模型已设置。文案生成尚未开放，请完成规格、积分价格与生成开放配置。</p>
    <div class="admin-table" tabindex="0" role="region" aria-label="文本模型配置列表，可横向滚动">
      <ElTable  :data="models" row-key="id" class="ui-data-table" empty-text="暂无记录" border><RowColumn  :min-width="140"><template #header>名称 / 模型</template><template #default="{ row: row }">{{ row.name }}<small>{{ row.model }}</small><small v-if="defaultModel?.model_config_id === row.id">工作台默认模型</small></template></RowColumn><RowColumn  :min-width="140"><template #header>模型地址</template><template #default="{ row: row }">{{ row.base_url }}</template></RowColumn><RowColumn  :min-width="140"><template #header>图片输入</template><template #default="{ row: row }">{{ row.supports_images ? '支持' : '不支持' }}</template></RowColumn><RowColumn  :min-width="140"><template #header>版本</template><template #default="{ row: row }">{{ row.revision }}</template></RowColumn><RowColumn  :min-width="140"><template #header>状态 / 密钥</template><template #default="{ row: row }">{{ row.enabled ? '启用' : '停用' }}<small>{{ row.has_api_key ? '密钥已配置' : '密钥未配置' }}</small><small v-if="defaultModel?.model_config_id === row.id && (!row.enabled || !row.has_api_key)" class="field-error">默认模型不可用，请启用或选择其他模型。</small></template></RowColumn><RowColumn  :min-width="140"><template #header>操作</template><template #default="{ row: row }"><div class="button-row"><UiButton class="button" :disabled="busy" @click="edit(row)">配置模型</UiButton><UiButton v-if="defaultModel?.model_config_id !== row.id" class="button" :disabled="busy || !row.enabled || !row.has_api_key || !defaultModel" @click="chooseDefault(row)">设为默认</UiButton></div></template></RowColumn></ElTable>
    </div>
    <p v-if="!busy && !error && !models.length">暂无文本模型配置。</p>
    <UiButton v-if="nextCursor" class="button" :disabled="busy" @click="load(true)">加载更多模型</UiButton>
  </section>
  <AppDrawer v-model:open="open" class="admin-overlay" :title="editing ? '编辑文本模型' : '新增文本模型'" purpose="edit" @update:open="value => { if (!value) draft.api_key = '' }">
    <form id="text-model-form" class="form-stack" @submit.prevent="save">
      <p v-if="editing">当前配置版本：{{ editing.revision }}</p>
      <label for="text-model-name">配置名称<UiInput id="text-model-name" v-model="draft.name" data-initial-focus required maxlength="100" /></label>
      <label for="text-model-provider">模型协议<UiSelect id="text-model-provider" v-model="draft.provider"><option value="openai_chat">OpenAI Chat 兼容协议</option></UiSelect></label>
      <label for="text-model-url">模型 API 地址<UiInput id="text-model-url" v-model="draft.base_url" type="url" required maxlength="2048" placeholder="https://models.example/v1" /></label>
      <label for="text-model-id">模型名称<UiInput id="text-model-id" v-model="draft.model" required maxlength="200" /></label>
      <label for="text-model-key">{{ editing ? '替换模型密钥（留空保留原密钥）' : '模型密钥' }}<UiInput id="text-model-key" v-model="draft.api_key" type="password" autocomplete="new-password" :required="!editing" maxlength="8192" /></label>
      <label for="text-model-images">支持图片输入<UiSelect id="text-model-images" v-model="draft.supports_images"><option :value="false">否</option><option :value="true">是</option></UiSelect></label>
      <label for="text-model-timeout">请求超时（秒）<UiInput id="text-model-timeout" v-model.number="draft.timeout_seconds" type="number" min="1" max="120" step="any" required /></label>
      <label for="text-model-temperature">温度（可选）<UiInput id="text-model-temperature" :value="draft.temperature" type="number" min="0" max="2" step="any" @input="optionalNumber($event, 'temperature')" /></label>
      <label for="text-model-tokens">最大输出 Token 数（可选）<UiInput id="text-model-tokens" :value="draft.max_tokens" type="number" min="1" step="1" @input="optionalNumber($event, 'max_tokens')" /></label>
      <label for="text-model-reasoning">推理强度<UiSelect id="text-model-reasoning" v-model="draft.reasoning_effort" aria-label="推理强度" aria-describedby="text-model-reasoning-help"><option value="">沿用模型默认</option><option v-for="effort in reasoningEfforts" :key="effort" :value="effort">{{ effort }}</option></UiSelect></label>
      <small id="text-model-reasoning-help">none 表示显式请求不推理。可用档位以模型服务支持为准。</small>
      <label v-if="editing" for="text-model-enabled">状态<UiSelect id="text-model-enabled" v-model="draft.enabled"><option :value="true">启用</option><option :value="false">停用</option></UiSelect></label>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
      <UiButton v-if="conflict" type="button" class="button" :disabled="busy" @click="reloadConflict">放弃草稿并载入最新配置</UiButton>
    </form>
    <template #actions><UiButton class="button primary" form="text-model-form" :disabled="busy || conflict">保存模型配置</UiButton></template>
  </AppDrawer>
  <AppDrawer v-model:open="defaultOpen" class="admin-overlay" title="设置默认文本模型" purpose="edit">
    <form id="text-default-form" class="form-stack" @submit.prevent="saveDefault">
      <p>工作台新提交的文案任务将使用 {{ selectedDefault?.name }}（{{ selectedDefault?.model }}）。已提交任务保留原模型。</p>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
      <UiButton v-if="defaultConflict" type="button" class="button" :disabled="busy" @click="reloadDefault">重新加载默认设置</UiButton>
    </form>
    <template #actions><UiButton class="button primary" form="text-default-form" :disabled="busy || defaultConflict">保存默认模型</UiButton></template>
  </AppDrawer>
</template>

<style scoped>
.button-row{display:flex;gap:8px;flex-wrap:wrap}td small{display:block;overflow-wrap:anywhere}
</style>
