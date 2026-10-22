<script setup lang="ts">
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import { ref, watch, onScopeDispose } from 'vue'
import { preparePrompt } from '../../api/assist'
import { createIntent, type Intent, ApiError } from '../../api/client'
import type { Schema } from '../../types/api'
import { session } from '../auth/session'
import { productLabels, parameterLabels } from './display'
const props = withDefaults(defineProps<{ modelValue: string; request: Schema<'AssistRequest'> | null; readonly?: boolean; disabled?: boolean; textareaId?: string; maxLength?: number }>(), { textareaId: 'creation-instruction' })
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const original = ref<string | undefined>(), busy = ref(false), error = ref('')
const missingFacts = ref<string[]>([])
function factLabel(name: string) { return productLabels[name] || parameterLabels[name.replace(/^parameters\./, '')] || ({ material_versions:'商品图片', original:'创作要求', efficacy:'功效依据', price:'商品价格', promotion:'优惠信息', 'parameters.platform':'目标平台', 'parameters.output_type':'图片用途', 'parameters.first_frame_file_id':'视频首帧' } as Record<string,string>)[name] || '相关商品信息' }
let intent: Intent<Schema<'AssistRequest'>> | undefined, revision = 0, alive = true, applied: string | undefined
onScopeDispose(() => { alive = false; revision++ })
watch(() => JSON.stringify(props.request), () => { revision++; if (props.request?.original !== applied) missingFacts.value = []; intent = undefined; error.value = '' }, { flush: 'sync' })
watch(() => props.modelValue, () => { revision++ }, { flush: 'sync' })
watch(() => props.disabled, () => { revision++ }, { flush: 'sync' })
async function assist() {
  if (!props.request || busy.value || props.readonly || props.disabled) return
  busy.value = true; error.value = ''
  const stamp = revision, epoch = session.epoch.value
  intent ??= createIntent(props.request)
  try {
    const result = await preparePrompt(intent)
    if (!alive || stamp !== revision || epoch !== session.epoch.value || props.disabled) return
    if (props.maxLength !== undefined && result.proposed.length > props.maxLength) {
      intent = undefined
      error.value = `AI 完善后的指令超过 ${props.maxLength} 字上限，原指令已保留。请精简创作要求后重试。`
      return
    }
    original.value ??= props.modelValue
    applied = result.proposed
    missingFacts.value = [...new Set((result.missing_facts || []).map(factLabel))]
    intent = undefined
    emit('update:modelValue', result.proposed)
  }
  catch (e) { if (alive && stamp === revision && epoch === session.epoch.value) error.value = e instanceof ApiError ? e.message : '辅助暂时不可用。' }
  finally { if (alive) busy.value = false }
}
function undo() { if (props.disabled) return; if (original.value !== undefined) emit('update:modelValue', original.value); original.value = undefined; applied = undefined; missingFacts.value = []; intent = undefined }
function input(event: Event) {
  if (props.disabled) return
  const value = (event.target as HTMLTextAreaElement).value
  emit('update:modelValue', props.maxLength === undefined ? value : value.slice(0, props.maxLength))
}
</script>
<template>
  <div class="prompt-editor">
    <div class="prompt-heading"><label :for="textareaId">创作指令</label>
    <UiButton v-if="!readonly" class="button assist-button" type="button" :disabled="!request || busy || disabled" @click="assist"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3Z M20 2v4 M18 4h4"/></svg>{{ busy ? '正在完善…' : intent ? '重试本次辅助' : 'AI 帮我完善' }}</UiButton>
    </div>
    <UiInput type="textarea" :id="textareaId" rows="4" :readonly="readonly" :disabled="disabled" :maxlength="maxLength" :value="modelValue" @input="input" />
    <p v-if="missingFacts.length" class="assist-facts" role="status">可补充的信息：{{ missingFacts.join('、') }}。请仅填写有依据的内容。</p>
    <UiButton v-if="original !== undefined" class="button undo-button" type="button" :disabled="disabled" @click="undo">撤回辅助，恢复原指令</UiButton>
    <p v-if="error" class="field-error" role="alert">{{ error }}</p>
  </div>
</template>
<style scoped>
.prompt-editor { display:grid; gap:8px }
.prompt-heading { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:4px 8px }
.prompt-heading>label { font-weight:600; color:var(--color-text); margin:0 }
.prompt-editor>textarea:where(:not([class*="el-"])) { height:96px; min-height:96px; resize:vertical }
.assist-button { justify-self:start; color:var(--color-primary); border-color:var(--color-border); background:var(--color-background); font-weight:600 }
.assist-button svg { width:16px; height:16px }
.assist-facts { font-size:12px; margin:0; color:var(--color-muted) }
.undo-button { justify-self:start; padding-inline:0; border:0; background:transparent; color:var(--color-primary); font-size:13px }
</style>
