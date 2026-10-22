<script setup lang="ts">
import { ElRadio } from 'element-plus/es/components/radio/index'
import UiSelect from '../../components/ui/UiSelect.vue'
import { useId, watch } from 'vue'
import { fileContentUrl } from '../../api/files'
import GenerationSettings from './GenerationSettings.vue'
import type { VideoOptions } from './videoParameters'
const props = defineProps<{ protocol: string; modelValue: Record<string, string | number | boolean>; materials: { file_id: string }[]; disabled?: boolean; videoOptions?: VideoOptions | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: Record<string, string | number | boolean>] }>()
const uid = useId()
const platforms = [ ['amazon', 'Amazon'], ['taobao', '淘宝'], ['tmall', '天猫'], ['jd', '京东'], ['pinduoduo', '拼多多'], ['shopee', 'Shopee'], ['lazada', 'Lazada'], ['shein', 'SHEIN'], ['temu', 'Temu'] ]
function selectPlatform(event: Event) {
  const platform = (event.target as HTMLSelectElement).value
  const output = props.modelValue.output_type
  emit('update:modelValue', { platform, ...(output ? { output_type: output } : {}) })
}
function selectOutput(event: Event) { emit('update:modelValue', { platform: String(props.modelValue.platform || ''), output_type: (event.target as HTMLSelectElement).value }) }
watch(() => [props.protocol, props.modelValue.first_frame_file_id, props.materials.map(m => m.file_id).join(',')], () => {
  if (props.protocol === 'video-agent-v1' && props.modelValue.first_frame_file_id && !props.materials.some(m => m.file_id === props.modelValue.first_frame_file_id)) {
    const next = { ...props.modelValue }; delete next.first_frame_file_id
    emit('update:modelValue', next)
  }
}, { immediate: true })
</script>
<template>
  <section v-if="protocol === 'image-agent-v1'" class="media-choices form-stack" aria-label="图片创作要求">
    <div><label :for="uid + '-platform'">目标平台 <small>必选</small></label><UiSelect :id="uid + '-platform'" aria-label="目标平台" :value="modelValue.platform || ''" required @change="selectPlatform"><option value="" disabled>请选择目标平台</option><option v-for="[value, label] in platforms" :key="value" :value="value">{{ label }}</option></UiSelect></div>
    <div><label :for="uid + '-output'">图片用途 <small>必选</small></label><UiSelect :id="uid + '-output'" aria-label="图片用途" :value="modelValue.output_type || ''" required @change="selectOutput"><option value="" disabled>请选择图片用途</option><option value="main_image">商品主图</option><option value="detail_page">详情图（3 张）</option><option value="pdd_white_background">白底图</option><option value="long_image">商品长图</option></UiSelect></div>
  </section>
  <template v-else-if="protocol === 'video-agent-v1'">
    <GenerationSettings v-if="videoOptions" :options="videoOptions" :model-value="modelValue" :disabled="disabled" @update:model-value="emit('update:modelValue', $event)" />
    <fieldset class="first-frame-choice"><legend>视频首帧 <small>必选</small></legend><p>从已上传商品图片中选择本次视频的首帧。</p><p v-if="!materials.length">上传商品图片后即可选择。</p><ElRadio :disabled="disabled" v-for="(material, index) in materials" :key="material.file_id" class="frame-option" :name="uid + '-first-frame'" :value="material.file_id" :model-value="modelValue.first_frame_file_id || ''" @change="emit('update:modelValue', { ...modelValue, first_frame_file_id: material.file_id })"><img :src="fileContentUrl(material.file_id)" :alt="'商品参考图 ' + (index + 1)" /><span>商品参考图 {{ index + 1 }}</span></ElRadio></fieldset>
  </template>
</template>
<style scoped>
.media-choices,.first-frame-choice { margin:0; padding:10px 0 0; border:0; border-top:1px solid var(--color-border) }
.media-choices { grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 12px }
.media-choices>div { min-width:0 }
.media-choices label { display:block; margin-bottom:6px }
small,.choice-note,.first-frame-choice p { color:var(--color-muted); font-size:13px }
.choice-note { grid-column:1 / -1; display:block; margin:0; line-height:1.6 }
.first-frame-choice legend { padding:0; font-weight:600; font-size:14px }
.first-frame-choice p { margin:8px 0 12px }
.frame-option { display:flex; align-items:center; gap:10px; min-height:60px; padding:6px 0; cursor:pointer; font-size:13px }
.frame-option input:where(:not([class*="el-"])) { width:18px; height:18px; accent-color:var(--color-primary); flex-shrink:0 }
.frame-option :deep(.el-radio__label) { display:flex; align-items:center; gap:10px; white-space:normal }
.frame-option img { width:48px; height:48px; object-fit:contain; background:var(--color-background); border-radius:6px }
@media(min-width:901px) and (max-width:1180px), (max-width:400px) { .media-choices { grid-template-columns:minmax(0,1fr) } }
</style>
