import '../../src/styles/element-components'
import { createApp, defineComponent, h, ref } from 'vue'
import MediaChoices from '../../src/features/workspace/MediaChoices.vue'
import VideoTaskPanel from '../../src/features/workspace/VideoTaskPanel.vue'
import MediaAgentConfigs from '../../src/features/admin/MediaAgentConfigs.vue'
import type { MediaTaskState } from '../../src/types/media'
import '../../src/styles/tokens.css'
import '../../src/styles/element-theme.css'
import '../../src/features/admin/admin.css'

const media = {
  kind: 'video', status: 'awaiting_confirmation', head_plan_version: 2,
  plan: { plan_version: 2, document: { creative: '展示商品外观与办公室使用场景', audience: '通勤人群',
    selling_points: ['轻便便携'], duration_seconds: 5, aspect_ratio: '9:16', subtitles: true,
    voiceover: false, music: false, shared_visual: { scene: '明亮办公室', lighting: '柔和自然光' },
    shots: [{ shot_id: 's1', content: '展示真实商品外观', action: '缓慢转动', camera: '轻推',
      start_frame: 0, end_frame: 150, subtitle_text: '日常随行' }] } },
} satisfies MediaTaskState
createApp(defineComponent({ setup() {
  const image = ref<Record<string,string|number|boolean>>({})
  const video = ref<Record<string,string|number|boolean>>({})
  const current = ref<MediaTaskState>(media)
  const materials = [{file_id:'00000000-0000-4000-8000-000000000001'}]
  return () => h('main',{class:'fixture'},[
    h('h1','媒体接入交互验证'),h('p','TEST_ONLY 合成资料'),
    h('section',{class:'panel'},[h('h2','图片创作'),h(MediaChoices,{
      protocol:'image-agent-v1',modelValue:image.value,materials:[],
      'onUpdate:modelValue':value=>{image.value=value}})]),
    h('section',{class:'panel'},[h('h2','视频创作'),h(MediaChoices,{
      protocol:'video-agent-v1',modelValue:video.value,materials,
      'onUpdate:modelValue':value=>{video.value=value}}),h(VideoTaskPanel,{
        taskId:'00000000-0000-4000-8000-000000000002',media:current.value,
        onChanged:()=>{current.value={kind:'video',status:'generating'}}}),
      h('button',{class:'button','data-input-state':'',onClick:()=>{
        current.value={kind:'video',status:'awaiting_input',questions:['请补充商品使用场景']}
      }},'查看补资料状态')]),
    h(MediaAgentConfigs,{kind:'image'}),h(MediaAgentConfigs,{kind:'video'})])
}})).mount('#app')
const style = document.createElement('style')
style.textContent = '.fixture{max-width:1100px;margin:auto;padding:24px;display:grid;gap:24px}.fixture>.panel{min-width:0}.fixture h1{font-size:26px}.fixture h2{font-size:20px}.fixture input,.fixture select,.fixture textarea{max-width:100%}@media(max-width:600px){.fixture{padding:16px}}'
document.head.append(style)
