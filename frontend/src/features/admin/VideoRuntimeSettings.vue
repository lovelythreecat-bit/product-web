<script setup lang="ts">
import { nextTick, onMounted, ref, shallowRef } from 'vue'
import AppDrawer from '../../components/AppDrawer.vue'
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import * as api from '../../api/mediaAgents'
import type { Json, MediaRecord } from '../../api/mediaAgents'
import { ApiError } from '../../api/client'
import { useAdminRequest } from './shared'

const emit=defineEmits<{closed:[];saved:[]}>()
const {busy,error,run}=useAdminRequest()
const original=shallowRef<MediaRecord|null>(null),conflict=ref(false)
const connectionRevision=ref(0),modeControl=ref<{focus:()=>void}>()
const ratios=['9:16','16:9','1:1','4:5','3:4','4:3','3:2','2:3']
const fields=[{key:'max_images',label:'每任务图片数量上限',min:1,max:12},
  {key:'max_file_bytes',label:'单文件上限（字节）',min:1,max:20971520},
  {key:'video_bitrate',label:'视频码率（bit/s）',min:1,max:undefined},
  {key:'audio_bitrate',label:'音频码率（bit/s）',min:1,max:undefined},
  {key:'lease_seconds',label:'工作项租约（秒）',min:15,max:undefined}]
const draft=ref({mode:'fake',duration_tiers:'',default_duration:0,values:{} as Record<string,number>,resolutions:{} as Record<string,number[]>})
onMounted(()=>run(async()=>{
  const before=await api.getMediaConnection('video')
  const value=await api.getMediaResource('video','settings')
  const after=await api.getMediaConnection('video')
  if(before.revision!==after.revision)throw new ApiError('服务连接已更新，请关闭后重新打开编辑。',409)
  connectionRevision.value=before.revision
  return value
},value=>{
  original.value=value;draft.value.mode=String(value.mode);draft.value.duration_tiers=(value.duration_tiers as number[]).join(', ')
  draft.value.default_duration=Number(value.default_duration)
  draft.value.values=Object.fromEntries(fields.map(field=>[field.key,Number(value[field.key])]))
  draft.value.resolutions=Object.fromEntries(Object.entries(value.resolutions as Record<string,number[]>).map(([key,pair])=>[key,[...pair]]))
  void nextTick(()=>modeControl.value?.focus())
}))
async function save(){if(!original.value||conflict.value)return
  await run(async()=>{try{
    const tiers=draft.value.duration_tiers.split(/[,，\s]+/).filter(Boolean).map(Number)
    if(!tiers.length||tiers.some(tier=>!Number.isInteger(tier)||tier<1||tier>30)||new Set(tiers).size!==tiers.length)throw new Error('时长档须为 1–30 的不重复整数，以逗号分隔。')
    if(!tiers.includes(draft.value.default_duration))throw new Error('默认时长必须属于时长档。')
    for(const ratio of ratios){const pair=draft.value.resolutions[ratio]??[],[rw,rh]=ratio.split(':').map(Number)
      if(pair.length!==2||pair.some(value=>!Number.isInteger(value)||value<=0||value%2!==0)||pair[0]!*rh! !== pair[1]!*rw!)throw new Error(`${ratio} 的宽高须为正偶数，并保持原比例。`)}
    const config:Record<string,Json>={expected_version:Number(original.value!.configuration_revision),mode:draft.value.mode,
      duration_tiers:tiers,default_duration:draft.value.default_duration,...draft.value.values,resolutions:draft.value.resolutions}
    return await api.saveVideoSettings(config,connectionRevision.value)
  }catch(e){if(e instanceof ApiError&&e.status===409)conflict.value=true;throw e}},()=>emit('saved'))}
</script>

<template>
  <AppDrawer :open="true" title="视频运行设置" purpose="edit" @update:open="value=>{if(!value&&!busy)emit('closed')}">
    <p v-if="busy&&!original" role="status">正在读取最新设置…</p>
    <form v-if="original" id="video-settings-form" class="form-stack" @submit.prevent="save">
      <fieldset class="form-stack" :disabled="busy">
        <label for="video-run-mode">出片方式<UiSelect id="video-run-mode" ref="modeControl" v-model="draft.mode" aria-label="出片方式" data-initial-focus><option value="fake">替身测试</option><option value="real">真实模型</option></UiSelect></label>
        <p class="field-hint">替身测试使用本地占位分镜和画面，仍由 FFmpeg 合成。真实出片需先配置分镜文本模型和视频生成模型。</p>
        <label for="video-duration-tiers">可选成片时长（秒）<UiInput id="video-duration-tiers" v-model="draft.duration_tiers" required aria-describedby="video-duration-help" /></label>
        <small id="video-duration-help">每档 1–30 秒，使用逗号分隔；与万相的单段时长上限分别设置。</small>
        <label for="video-default-duration">默认成片时长（秒）<UiSelect id="video-default-duration" v-model="draft.default_duration" aria-label="默认成片时长（秒）" required><option v-for="tier in draft.duration_tiers.split(/[,，\s]+/).filter(Boolean).map(Number)" :key="tier" :value="tier">{{ tier }} 秒</option></UiSelect></label>
        <details><summary>文件与编码设置</summary><div class="form-stack advanced-fields"><label v-for="field in fields" :key="field.key" :for="'video-setting-'+field.key">{{ field.label }}<UiInput :id="'video-setting-'+field.key" v-model.number="draft.values[field.key]" type="number" :min="field.min" :max="field.max" step="1" required /></label></div></details>
        <details><summary>输出分辨率</summary><p class="field-hint">宽高须为正偶数，并保持对应比例。</p><div v-for="ratio in ratios" :key="ratio" class="resolution-row"><span>{{ ratio }}</span><label :for="'video-width-'+ratio">宽（像素）<UiInput :id="'video-width-'+ratio" v-model.number="draft.resolutions[ratio]![0]" type="number" min="2" step="2" required /></label><label :for="'video-height-'+ratio">高（像素）<UiInput :id="'video-height-'+ratio" v-model.number="draft.resolutions[ratio]![1]" type="number" min="2" step="2" required /></label></div></details>
      </fieldset>
    </form>
    <p v-if="error" class="field-error" role="alert">{{ error }}</p>
    <template #actions><UiButton class="button primary" form="video-settings-form" :disabled="busy||conflict||!original">保存运行设置</UiButton></template>
  </AppDrawer>
</template>

<style scoped>
fieldset{min-width:0;border:0;padding:0;margin:0}.advanced-fields{padding-top:16px}.resolution-row{display:grid;grid-template-columns:40px minmax(0,1fr) minmax(0,1fr);gap:12px;align-items:center;margin-top:16px}.resolution-row label{min-width:0}summary{cursor:pointer;padding:12px 0}
</style>
