<script setup lang="ts">
import { ElCheckbox } from 'element-plus/es/components/checkbox/index'
import UiInput from '../../components/ui/UiInput.vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import UiButton from '../../components/ui/UiButton.vue'
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import * as api from '../../api/mediaAgents'
import { recordId } from '../../api/mediaAgents'
import type { Json, MediaKind, MediaRecord, MediaResource, MediaRole } from '../../api/mediaAgents'
import { ApiError, createIntent, type Intent } from '../../api/client'
import AppDrawer from '../../components/AppDrawer.vue'
import { useAdminRequest } from './shared'

const props = defineProps<{ kind: MediaKind; resource: MediaResource; record?: MediaRecord }>()
const emit = defineEmits<{ closed: []; saved: [] }>()
const { busy, error, run } = useAdminRequest()
const open = ref(true), loaded = ref(false), conflict = ref(false)
const original = shallowRef<MediaRecord>({}), options = shallowRef<MediaRecord[]>([]), adapterTypes = shallowRef<MediaRecord[]>([])
const roles: {key:MediaRole;label:string}[] = [{key:'planner',label:'方案规划'},{key:'video',label:'视频生成'},
  {key:'voice',label:'配音'},{key:'music',label:'音乐'},{key:'visual',label:'视觉检查'}]
const runtimeFields = [{key:'request_timeout_seconds',label:'模型请求超时（秒）',min:0.1,max:undefined},
  {key:'model_concurrency',label:'模型并发上限',min:1,max:undefined},
  {key:'generation_reference_limit',label:'生图参考图片上限',min:1,max:undefined},
  {key:'vision_image_limit',label:'视觉图片上限',min:1,max:undefined},
  {key:'model_completion_attempts',label:'模型补齐尝试上限',min:1,max:8}]
const settingsFields = [{key:'max_images',label:'每任务图片数量上限',min:1,max:12},
  {key:'max_file_bytes',label:'单文件上限（字节）',min:1,max:20971520},
  {key:'video_bitrate',label:'视频码率（bit/s）',min:1,max:undefined},
  {key:'audio_bitrate',label:'音频码率（bit/s）',min:1,max:undefined},
  {key:'lease_seconds',label:'工作项租约（秒）',min:15,max:undefined}]
const labels: Record<MediaResource,string> = {services:'服务配置','model-configs':'模型配置','agent-configs':'Agent 方案',
  'model-profiles':'视频模型配置','adapter-bindings':'角色绑定',settings:'公共设置','adapter-types':'适配器能力'}
const singleton = computed(() => props.resource==='adapter-bindings' || props.resource==='settings')
const editing = computed(() => !!props.record || singleton.value)
const title = computed(() => (editing.value?'编辑':'新增') + labels[props.resource])
const draft = ref({ name:'',base_url:'',model:'',protocol:'openai_images',api_key:'',enabled:true,
  generation_path:'',edit_path:'',chat_path:'/chat/completions',service_id:'',description:'',
  parameters:{} as Record<string,Json>,image_models:{pro:'',fast:'',base:''} as Record<string,string>,
  stages:{} as Record<string,string>,role:'planner' as MediaRole,adapter:'',parameters_json:'{}',
  max_segment_seconds:1,bindings:{} as Record<MediaRole,string>,mode:'fake',duration_tiers:'',default_duration:0,
  settings:{} as Record<string,number>,resolutions:'{}' })
const secrets = ref<Record<string,string>>({}), clearSecrets = ref<Record<string,boolean>>({})
let creationIntent: Intent<{config:Record<string,Json>}> | null = null
const availableAdapters = computed(() => adapterTypes.value.filter(item => item.roles?.includes(draft.value.role)))
const selectedAdapter = computed(() => availableAdapters.value.find(item => item.adapter===draft.value.adapter))
const secretFields = computed(() => [...new Set([...(selectedAdapter.value?.secret_fields ?? []),
  ...Object.keys(original.value.secret_presence ?? {})])])
const stageNames = computed(() => [...new Set(['vision',...Object.keys(draft.value.stages)])])
const enabledOptions = computed(() => options.value.filter(row => row.enabled))
const text = (value:unknown) => typeof value==='string'?value:''
const asObject = (value:unknown):Record<string,Json> => value && typeof value==='object' && !Array.isArray(value) ? value as Record<string,Json> : {}
function optionLabel(row:MediaRecord) { return `${row.name || row.model || row.adapter || '未命名'} · ${recordId(row).slice(0,8)}` }
function hasOption(id:string) { return enabledOptions.value.some(item => recordId(item)===id) }
function roleProfiles(role:MediaRole) { return enabledOptions.value.filter(item => item.role===role) }
function populate(value:MediaRecord) {
  original.value=value
  const parameters=asObject(value.parameters)
  draft.value.name=text(value.name);draft.value.base_url=text(value.base_url);draft.value.model=text(value.model)
  draft.value.protocol=text(value.protocol)||'openai_images';draft.value.enabled=value.enabled!==false
  draft.value.service_id=text(value.service_id);draft.value.description=text(value.description)
  draft.value.generation_path=text(value.generation_path);draft.value.edit_path=text(value.edit_path)
  draft.value.chat_path=text(value.chat_path)||'/chat/completions'
  draft.value.parameters={http_proxy:null,request_timeout_seconds:180,model_concurrency:2,
    generation_reference_limit:4,vision_image_limit:12,model_completion_attempts:4,...parameters}
  draft.value.image_models={pro:'',fast:'',base:'',...value.image_models}
  draft.value.stages={...value.stages};draft.value.role=value.role??'planner';draft.value.adapter=text(value.adapter)
  draft.value.parameters_json=JSON.stringify(parameters,null,2)
  draft.value.max_segment_seconds=Number(parameters.max_segment_seconds??1)
  for(const role of roles) { const target=asObject(value[role.key]);draft.value.bindings[role.key]=text(target.profile_id)||'@'+text(target.adapter) }
  draft.value.mode=text(value.mode);draft.value.duration_tiers=Array.isArray(value.duration_tiers)?value.duration_tiers.join(', '):''
  draft.value.default_duration=Number(value.default_duration??0)
  draft.value.settings=Object.fromEntries(settingsFields.map(field=>[field.key,Number(value[field.key]??0)]))
  draft.value.resolutions=JSON.stringify(value.resolutions??{},null,2)
}
async function initialize() {
  await run(async () => {
    const value = editing.value ? await api.getMediaResource(props.kind,props.resource,
      singleton.value?undefined:recordId(props.record!)) : {}
    let choices:MediaRecord[]=[],types:MediaRecord[]=[]
    if(props.resource==='model-configs') choices=await api.loadMediaOptions('image','services')
    if(props.resource==='agent-configs') choices=await api.loadMediaOptions('image','model-configs')
    if(props.resource==='adapter-bindings') choices=await api.loadMediaOptions('video','model-profiles')
    if(props.resource==='model-profiles') { const result=await api.listMediaResources('video','adapter-types');types=Array.isArray(result)?result:[] }
    return {value,choices,types}
  },({value,choices,types})=>{options.value=choices;adapterTypes.value=types;populate(value);loaded.value=true})
}
function objectJson(input:string,label:string) {
  try { const result:unknown=JSON.parse(input);if(!result || typeof result!=='object'||Array.isArray(result)) throw new Error();return result as Record<string,Json> }
  catch { throw new Error(label+'必须是有效的 JSON 对象。') }
}
function buildConfig():Record<string,Json> {
  const value=draft.value
  const version=editing.value?{[props.kind==='image'?'version':'expected_version']:
    Number(singleton.value?original.value.configuration_revision:original.value.version)}:{}
  if(props.resource==='services') return {...version,name:value.name,base_url:value.base_url,protocol:value.protocol,
    generation_path:value.generation_path||null,edit_path:value.edit_path||null,chat_path:value.chat_path,enabled:value.enabled,
    ...(value.api_key?{api_key:value.api_key}:{})}
  if(props.resource==='model-configs') return {...version,service_id:value.service_id,model:value.model,
    description:value.description||null,enabled:value.enabled}
  if(props.resource==='agent-configs') {
    const aliases=Object.fromEntries(Object.entries(value.image_models).filter(([,id])=>id))
    if(!Object.keys(aliases).length) throw new Error('请至少配置一个生图别名。')
    return {...version,name:value.name,parameters:{...value.parameters},image_models:aliases,
      stages:Object.fromEntries(Object.entries(value.stages).filter(([,id])=>id)),enabled:value.enabled}
  }
  if(props.resource==='model-profiles') {
    const parameters=objectJson(value.parameters_json,'模型参数')
    if(value.adapter==='wan') parameters.max_segment_seconds=Number(value.max_segment_seconds)
    const replacements=Object.fromEntries(Object.entries(secrets.value).filter(([,secret])=>secret!==''))
    const cleared=Object.keys(clearSecrets.value).filter(key=>clearSecrets.value[key])
    if(cleared.some(key=>replacements[key])) throw new Error('同一密钥不能同时替换和清除。')
    return {...version,name:value.name,role:value.role,adapter:value.adapter,base_url:value.base_url||null,
      model:value.model||null,parameters,enabled:value.enabled,...(Object.keys(replacements).length?{secrets:replacements}:{}),
      ...(cleared.length?{clear_secrets:cleared}:{})}
  }
  if(props.resource==='adapter-bindings') return {...version,...Object.fromEntries(roles.map(({key})=>{
    const target=value.bindings[key];const binding:Record<string,Json>=target.startsWith('@')?{adapter:target.slice(1),profile_id:null}:{profile_id:target};return [key,binding]
  }))}
  const tiers=value.duration_tiers.split(/[,，\s]+/).filter(Boolean).map(Number)
  if(!tiers.length||tiers.some(tier=>!Number.isInteger(tier)||tier<1||tier>30)||new Set(tiers).size!==tiers.length) throw new Error('时长档须为 1–30 的不重复整数，以逗号分隔。')
  if(!tiers.includes(Number(value.default_duration))) throw new Error('默认时长必须属于时长档。')
  return {...version,mode:value.mode,duration_tiers:tiers,default_duration:Number(value.default_duration),
    ...value.settings,resolutions:objectJson(value.resolutions,'分辨率映射')}
}
async function save() {
  if(!loaded.value||conflict.value) return
  await run(async()=>{
    try{
      const config=buildConfig(),identity=singleton.value?undefined:recordId(props.record??{})||undefined
      if(!editing.value){
        if(creationIntent?.body!==JSON.stringify({config})) creationIntent=createIntent({config})
        return await api.saveMediaResource(props.kind,props.resource,identity,config,true,creationIntent)
      }
      return await api.saveMediaResource(props.kind,props.resource,identity,config,false)
    }
    catch(e){if(e instanceof ApiError&&e.status===409)conflict.value=true;throw e}
  },()=>{draft.value.api_key='';secrets.value={};creationIntent=null;emit('saved')})
}
function close(value:boolean) { if(!value){draft.value.api_key='';secrets.value={};clearSecrets.value={};creationIntent=null;emit('closed')} }
onBeforeUnmount(()=>{draft.value.api_key='';secrets.value={};clearSecrets.value={};creationIntent=null})
onMounted(initialize)
</script>

<template>
  <AppDrawer :open="open" class="admin-overlay" :title="title" purpose="edit" @update:open="close">
    <p v-if="busy && !loaded" role="status">正在读取最新配置…</p>
    <form v-if="loaded" id="media-resource-form" class="form-stack" @submit.prevent="save">
      <template v-if="!singleton">
        <label v-if="resource!=='model-configs'" for="media-resource-name">配置名称<UiInput id="media-resource-name" v-model="draft.name" data-initial-focus required maxlength="200" /></label>
        <template v-if="resource==='services'">
          <label for="media-resource-protocol">调用协议<UiSelect id="media-resource-protocol" v-model="draft.protocol"><option value="openai_images">OpenAI Images</option><option value="openrouter_images">OpenRouter Images</option><option value="chat_completions">Chat Completions（视觉）</option></UiSelect></label>
          <label for="media-resource-url">供应商 API 地址<UiInput id="media-resource-url" v-model="draft.base_url" type="url" required maxlength="2048" /></label>
          <label for="media-resource-key">{{ editing?'替换供应商密钥（留空保留）':'供应商密钥' }}<UiInput id="media-resource-key" v-model="draft.api_key" type="password" autocomplete="new-password" :required="!editing" maxlength="8192" /></label>
          <details><summary>高级接口路径</summary><div class="form-stack"><label for="media-generation-path">图片生成路径（可选）<UiInput id="media-generation-path" v-model="draft.generation_path" maxlength="512" /></label><label for="media-edit-path">图片编辑路径（可选）<UiInput id="media-edit-path" v-model="draft.edit_path" maxlength="512" /></label><label for="media-chat-path">视觉调用路径<UiInput id="media-chat-path" v-model="draft.chat_path" required maxlength="512" /></label></div></details>
        </template>
        <template v-if="resource==='model-configs'">
          <label for="media-model-service">所属服务<UiSelect id="media-model-service" v-model="draft.service_id" data-initial-focus required><option value="">请选择服务</option><option v-if="draft.service_id && !hasOption(draft.service_id)" :value="draft.service_id">当前服务（{{ draft.service_id }}）</option><option v-for="row in enabledOptions" :key="recordId(row)" :value="recordId(row)">{{ optionLabel(row) }}</option></UiSelect></label>
          <label for="media-model-name">供应商模型名称<UiInput id="media-model-name" v-model="draft.model" required maxlength="300" /></label>
          <label for="media-model-description">用途说明<UiInput type="textarea" id="media-model-description" v-model="draft.description" rows="3" maxlength="2000" /></label>
        </template>
        <template v-if="resource==='agent-configs'">
          <fieldset><legend>生图模型别名</legend><p class="field-hint">至少配置一个别名，工作台默认生图选择来自此处。</p><label v-for="alias in ['pro','fast','base']" :key="alias" :for="'media-alias-'+alias">{{ alias }}<UiSelect :id="'media-alias-'+alias" v-model="draft.image_models[alias]"><option value="">不配置</option><option v-if="draft.image_models[alias] && !hasOption(draft.image_models[alias]!)" :value="draft.image_models[alias]">当前模型（{{ draft.image_models[alias] }}）</option><option v-for="row in enabledOptions" :key="recordId(row)" :value="recordId(row)">{{ optionLabel(row) }}</option></UiSelect></label></fieldset>
          <fieldset><legend>视觉阶段模型</legend><label v-for="stage in stageNames" :key="stage" :for="'media-stage-'+stage">{{ stage==='vision'?'视觉分析（vision）':stage }}<UiSelect :id="'media-stage-'+stage" v-model="draft.stages[stage]" :required="stage==='vision'"><option value="">请选择模型</option><option v-if="draft.stages[stage] && !hasOption(draft.stages[stage]!)" :value="draft.stages[stage]">当前模型（{{ draft.stages[stage] }}）</option><option v-for="row in enabledOptions" :key="recordId(row)" :value="recordId(row)">{{ optionLabel(row) }}</option></UiSelect></label></fieldset>
          <details><summary>运行参数</summary><div class="form-stack"><label v-for="field in runtimeFields" :key="field.key" :for="'media-runtime-'+field.key">{{ field.label }}<UiInput :id="'media-runtime-'+field.key" v-model.number="draft.parameters[field.key] as number" type="number" :min="field.min" :max="field.max" :step="field.key==='request_timeout_seconds'?'any':1" required /></label><label for="media-http-proxy">HTTP 代理（可选）<UiInput id="media-http-proxy" :value="draft.parameters.http_proxy as string" type="url" @input="draft.parameters.http_proxy=($event.target as HTMLInputElement).value||null" /></label></div></details>
        </template>
        <template v-if="resource==='model-profiles'">
          <label for="media-video-role">模型角色<UiSelect id="media-video-role" v-model="draft.role" @change="draft.adapter='';secrets={};clearSecrets={}"><option v-for="role in roles" :key="role.key" :value="role.key">{{ role.label }}</option></UiSelect></label>
          <label for="media-video-adapter">适配器<UiSelect id="media-video-adapter" v-model="draft.adapter" required><option value="">请选择适配器</option><option v-if="draft.adapter && !selectedAdapter" :value="draft.adapter">{{ draft.adapter }}（当前值）</option><option v-for="row in availableAdapters" :key="row.adapter" :value="row.adapter">{{ row.adapter }}</option></UiSelect></label>
          <p v-if="!availableAdapters.length" class="field-hint">当前服务没有提供此角色的可配置适配器。</p>
          <label for="media-video-url">供应商 API 地址<UiInput id="media-video-url" v-model="draft.base_url" type="url" :required="selectedAdapter?.required_fields?.includes('base_url')" maxlength="2000" /></label>
          <label for="media-video-model">供应商模型名称<UiInput id="media-video-model" v-model="draft.model" :required="selectedAdapter?.required_fields?.includes('model')" maxlength="200" /></label>
          <label v-if="draft.adapter==='wan'" for="media-wan-seconds">单镜头时长上限（秒）<UiInput id="media-wan-seconds" v-model.number="draft.max_segment_seconds" type="number" min="1" max="15" step="1" required /></label>
          <template v-for="field in secretFields" :key="field"><label :for="'media-secret-'+field">{{ field==='api_key'?'模型 API 密钥':field }}{{ editing?'（留空保留）':'' }}<UiInput :id="'media-secret-'+field" v-model="secrets[field]" type="password" autocomplete="new-password" :required="!editing && selectedAdapter?.required_fields?.includes(field)" maxlength="8192" /></label><ElCheckbox v-if="editing && original.secret_presence?.[field]" v-model="clearSecrets[field]" class="checkbox-row">明确清除已保存的 {{ field }}</ElCheckbox></template>
          <details><summary>其他模型参数</summary><label for="media-video-parameters">非敏感参数（JSON 对象）<UiInput type="textarea" id="media-video-parameters" v-model="draft.parameters_json" rows="6" spellcheck="false" /></label><p class="field-hint">密钥请填写在密钥字段中；未修改的其他参数会保留。</p></details>
        </template>
        <label for="media-resource-enabled">配置状态<UiSelect id="media-resource-enabled" v-model="draft.enabled"><option :value="true">启用</option><option :value="false">停用</option></UiSelect></label>
      </template>
      <template v-else-if="resource==='adapter-bindings'">
        <label v-for="role in roles" :key="role.key" :for="'media-binding-'+role.key">{{ role.label }}<UiSelect :id="'media-binding-'+role.key" v-model="draft.bindings[role.key]" required><option value="">请选择模型配置</option><option value="@fake">替身适配器（fake）</option><option v-if="role.key!=='planner' && role.key!=='video'" value="@none">不使用（none）</option><option v-if="draft.bindings[role.key] && !draft.bindings[role.key].startsWith('@') && !roleProfiles(role.key).some(row=>recordId(row)===draft.bindings[role.key])" :value="draft.bindings[role.key]">当前绑定（{{ draft.bindings[role.key] }}）</option><option v-for="row in roleProfiles(role.key)" :key="recordId(row)" :value="recordId(row)">{{ optionLabel(row) }} · {{ row.adapter }}</option></UiSelect></label>
      </template>
      <template v-else-if="resource==='settings'">
        <label for="media-settings-mode">运行模式<UiSelect id="media-settings-mode" v-model="draft.mode"><option value="fake">替身模式</option><option value="real">真实模型</option></UiSelect></label>
        <label for="media-settings-tiers">视频时长档（秒，以逗号分隔）<UiInput id="media-settings-tiers" v-model="draft.duration_tiers" required /></label>
        <label for="media-settings-duration">默认视频时长（秒）<UiInput id="media-settings-duration" v-model.number="draft.default_duration" type="number" min="1" max="30" step="1" required /></label>
        <details><summary>容量、编码与分辨率设置</summary><div class="form-stack"><label v-for="field in settingsFields" :key="field.key" :for="'media-settings-'+field.key">{{ field.label }}<UiInput :id="'media-settings-'+field.key" v-model.number="draft.settings[field.key]" type="number" :min="field.min" :max="field.max" step="1" required /></label><label for="media-settings-resolutions">画面比例到宽高的映射（JSON 对象）<UiInput type="textarea" id="media-settings-resolutions" v-model="draft.resolutions" rows="12" spellcheck="false" /></label></div></details>
      </template>
      <p v-if="conflict" class="field-hint">草稿已保留，请关闭后重新打开编辑。</p>
    </form>
    <p v-if="error" class="field-error" role="alert">{{ error }}</p>
    <template #actions><UiButton class="button primary" form="media-resource-form" data-save-resource :disabled="busy || !loaded || conflict">保存配置</UiButton></template>
  </AppDrawer>
</template>

<style scoped>
fieldset{min-width:0;margin:0;padding:16px;border:1px solid var(--color-border);border-radius:8px;display:grid;gap:16px}legend{padding:0 6px;font-size:14px;font-weight:600}.checkbox-row{display:flex;align-items:center;gap:8px;min-height:44px}.checkbox-row input:where(:not([class*="el-"])){width:auto;min-height:24px}textarea:where(:not([class*="el-"])){max-width:100%;resize:vertical}.form-stack{min-width:0}
</style>
