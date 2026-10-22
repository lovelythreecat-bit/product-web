<script setup lang="ts">
import { ref, watch, useId } from 'vue'
import { ElOption, ElSelect } from 'element-plus/es/components/select/index'
import AppDialog from '../../components/AppDialog.vue'
import UiButton from '../../components/ui/UiButton.vue'
import TextChoices from '../workspace/TextChoices.vue'
import { validateTextParameters } from '../workspace/textParameters'
import { copyTypeChoices } from './useQuickGeneration'

const props = defineProps<{ open: boolean; types: string[]; parameters: Record<string, string | number | boolean>; busy: boolean; error: string; credits: number | null; prepared?: boolean; uncertain?: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean]; change: [types: string[], parameters: Record<string, string | number | boolean>]; confirm: [types: string[], parameters: Record<string, string | number | boolean>] }>()
const choices = copyTypeChoices
const types = ref<string[]>([]), parameters = ref<Record<string, string | number | boolean>>({}), localError = ref('')
const id = useId()
watch(() => props.open, open => {
  if (!open) return
  types.value = props.types.length ? [...props.types] : [...choices]
  const { copy_type: _type, audience: _audience, max_chars: _max, extra_instructions: _extra, ...rest } = props.parameters
  parameters.value = { platform: '淘宝', tone: '自然', ...rest }; localError.value = ''
  emit('change', [...types.value], { ...parameters.value })
}, { immediate: true })
watch([types, parameters], () => {
  if (props.open && !props.prepared) emit('change', [...types.value], { ...parameters.value })
}, { deep: true })
function confirm() {
  localError.value = validateTextParameters(parameters.value)
  const selected = [...new Set(types.value.map(value => value.trim()))]
  if (!selected.length) localError.value = '请选择至少一种文案类型。'
  if (selected.some(value => !value || value.length > 100)) localError.value = '文案类型请填写 1–100 个字符。'
  if (localError.value) return
  emit('confirm', selected, { ...parameters.value })
}
</script>
<template>
  <AppDialog :open="open" title="文案创作要求" purpose="charge" @update:open="!busy && emit('update:open', $event)">
    <fieldset class="quick-copy-requirements" :disabled="busy || prepared">
      <label :for="id + '-types'">文案类型 <small>可多选、可自定义</small></label>
      <ElSelect :id="id + '-types'" v-model="types" aria-label="文案类型" multiple filterable allow-create default-first-option :multiple-limit="7" :disabled="busy || prepared" placeholder="选择或填写文案类型">
        <ElOption v-for="choice in choices" :key="choice" :value="choice" :label="choice" />
      </ElSelect>
      <TextChoices v-model="parameters" hide-copy-type hide-writing-limits />
    </fieldset>
    <p class="quick-charge-total" aria-live="polite"><span>使用</span><strong>{{ credits === null ? '—' : credits }} <small>积分</small></strong></p>
    <p v-if="localError || error" class="field-error" role="alert">{{ localError || error }}</p>
    <template #actions><UiButton class="button primary" type="button" :disabled="busy" @click="confirm">{{ busy ? '正在提交…' : uncertain ? '核对原批次' : '确认生成文案' }}</UiButton></template>
  </AppDialog>
</template>
<style scoped>
.quick-copy-requirements { border:0; padding:0; margin:0; min-width:0 }
.quick-copy-requirements>label { display:block; margin-bottom:8px }
.quick-copy-requirements>label small { color:var(--color-muted); font-weight:400; margin-left:8px }
.quick-copy-requirements .text-choices { border:0; padding-top:16px }
</style>
