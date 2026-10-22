<script setup lang="ts">
import UiInput from '../../components/ui/UiInput.vue'
import { computed, useId } from 'vue'
import { validateTextParameters } from './textParameters'

const props = withDefaults(defineProps<{ modelValue: Record<string, string | number | boolean>; hideCopyType?: boolean; hideWritingLimits?: boolean; extraLabel?: string }>(), { extraLabel: '额外协作要求' })
const emit = defineEmits<{ 'update:modelValue': [value: Record<string, string | number | boolean>] }>()
const uid = useId()
const copyTypes = ['宣传文案', '商品标题', '卖点描述', '详情介绍', '社交平台文案', '直播口播', '营销策略']
const platforms = ['淘宝', '天猫', '京东', '拼多多', '小红书', '抖音', '微信公众号', 'Amazon', '独立站']
const tones = ['自然', '活泼', '专业', '亲切', '简洁直接']
const maximumError = computed(() => validateTextParameters({ max_chars: props.modelValue.max_chars }))

function update(key: string, event: Event) {
  const raw = (event.target as HTMLInputElement | HTMLTextAreaElement).value
  const next = { ...props.modelValue }
  if (raw === '') delete next[key]
  else next[key] = key === 'max_chars' ? Number(raw) : raw
  emit('update:modelValue', next)
}
</script>

<template>
  <section class="text-choices form-stack" aria-label="文本创作要求">
    <div v-if="!hideCopyType">
      <label :for="uid + '-copy'">文案类型</label>
      <UiInput :id="uid + '-copy'" aria-label="文案类型" :suggestions="copyTypes" :value="modelValue.copy_type || ''" placeholder="宣传文案，可自定义" @input="update('copy_type', $event)" />
    </div>
    <div>
      <label :for="uid + '-platform'">目标平台</label>
      <UiInput :id="uid + '-platform'" aria-label="目标平台" :suggestions="platforms" :value="modelValue.platform || ''" placeholder="选择或填写发布平台" @input="update('platform', $event)" />
    </div>
    <div>
      <label :for="uid + '-tone'">语气</label>
      <UiInput :id="uid + '-tone'" aria-label="语气" :suggestions="tones" :value="modelValue.tone || ''" placeholder="自然，可自定义" @input="update('tone', $event)" />
    </div>
    <div v-if="!hideWritingLimits" class="text-choice-wide">
      <label :for="uid + '-maximum'">最大字符数</label>
      <UiInput :id="uid + '-maximum'" aria-label="最大字符数" type="number" min="1" step="1" inputmode="numeric" :value="modelValue.max_chars ?? ''" placeholder="留空表示不限制" :aria-invalid="maximumError ? 'true' : undefined" :aria-describedby="uid + '-maximum-help' + (maximumError ? ' ' + uid + '-maximum-error' : '')" @input="update('max_chars', $event)" />
      <small :id="uid + '-maximum-help'">标点、空格和换行均计入字符数。</small>
      <p v-if="maximumError" :id="uid + '-maximum-error'" class="field-error" role="alert">{{ maximumError }}</p>
    </div>
    <div v-if="!hideWritingLimits" class="text-choice-wide">
      <label :for="uid + '-extra'">{{ extraLabel }}</label>
      <UiInput type="textarea" :id="uid + '-extra'" :aria-label="extraLabel" :value="String(modelValue.extra_instructions || '')" rows="3" placeholder="如：先讲使用场景，再列卖点；避免夸张口号" @input="update('extra_instructions', $event)" />
    </div>
  </section>
</template>

<style scoped>
.text-choices { padding-top:10px; border-top:1px solid var(--color-border); grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 12px }
.text-choices>div { min-width:0 }
.text-choices label { display:block; margin-bottom:6px }
.text-choice-wide { grid-column:1 / -1 }
.text-choices small { display:block; margin-top:6px; color:var(--color-muted); font-size:13px; line-height:1.6 }
.text-choices textarea:where(:not([class*="el-"])) { resize:vertical }
@media(min-width:901px) and (max-width:1180px), (max-width:400px) { .text-choices { grid-template-columns:minmax(0,1fr) } }
</style>
