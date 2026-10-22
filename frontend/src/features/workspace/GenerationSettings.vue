<script setup lang="ts">
import { useId, watch } from 'vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import type { VideoOptions } from './videoParameters'

const props = defineProps<{ modelValue: Record<string, string | number | boolean>; options: VideoOptions; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: Record<string, string | number | boolean>] }>()
const uid = useId()
watch(() => [props.options, props.modelValue, props.disabled], () => {
  if (props.disabled) return
  const next = { ...props.modelValue }
  if (next.duration_seconds === undefined) next.duration_seconds = props.options.default_duration
  if (next.aspect_ratio === undefined) next.aspect_ratio = props.options.aspect_ratios.includes('9:16') ? '9:16' : props.options.aspect_ratios[0]!
  if (next.duration_seconds !== props.modelValue.duration_seconds || next.aspect_ratio !== props.modelValue.aspect_ratio) emit('update:modelValue', next)
}, { immediate: true })
function update(key: string, event: Event) {
  const value = (event.target as HTMLSelectElement).value
  emit('update:modelValue', { ...props.modelValue, [key]: key === 'duration_seconds' ? Number(value) : value })
}
</script>
<template>
  <section class="video-settings form-stack" aria-label="视频生成设置">
    <div><label :for="uid + '-duration'">视频时长</label><UiSelect :id="uid + '-duration'" aria-label="视频时长" :disabled="disabled" :value="modelValue.duration_seconds ?? options.default_duration" @change="update('duration_seconds', $event)"><option v-if="modelValue.duration_seconds !== undefined && !options.duration_tiers.includes(Number(modelValue.duration_seconds))" :value="modelValue.duration_seconds" disabled>{{ modelValue.duration_seconds }} 秒（需重新选择）</option><option v-for="seconds in options.duration_tiers" :key="seconds" :value="seconds">{{ seconds }} 秒</option></UiSelect></div>
    <div><label :for="uid + '-ratio'">画面比例</label><UiSelect :id="uid + '-ratio'" aria-label="画面比例" :disabled="disabled" :value="modelValue.aspect_ratio || '9:16'" @change="update('aspect_ratio', $event)"><option v-if="modelValue.aspect_ratio && !options.aspect_ratios.includes(String(modelValue.aspect_ratio))" :value="modelValue.aspect_ratio" disabled>{{ modelValue.aspect_ratio }}（需重新选择）</option><option v-for="ratio in options.aspect_ratios" :key="ratio" :value="ratio">{{ ratio }}</option></UiSelect></div>
  </section>
</template>
<style scoped>
.video-settings { padding-top:10px; border-top:1px solid var(--color-border); grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 12px }
.video-settings>div { min-width:0 }
.video-settings label { display:block; margin-bottom:6px }
@media(min-width:901px) and (max-width:1180px), (max-width:400px) { .video-settings { grid-template-columns:minmax(0,1fr) } }
</style>
