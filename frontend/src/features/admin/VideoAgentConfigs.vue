<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import AppDrawer from '../../components/AppDrawer.vue'
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import * as api from '../../api/mediaAgents'
import type { MediaConnection, VideoModels, VideoModelRole, VideoAdapter, VideoModelWrite } from '../../api/mediaAgents'
import { ApiError } from '../../api/client'
import VideoRuntimeSettings from './VideoRuntimeSettings.vue'
import { useAdminRequest } from './shared'

const {busy,error,run}=useAdminRequest()
const connection=shallowRef<MediaConnection|null>(null), models=shallowRef<VideoModels|null>(null)
const runtimeSummary=shallowRef<api.MediaRecord|null>(null)
const open=ref<'connection'|'sound'|VideoModelRole|null>(null),runtime=ref(false),conflict=ref(false),notice=ref('')
const sound=ref({revision:0,enabled:false}),soundDraft=ref(false)
const connectionDraft=ref({base_url:'',service_key:'',management_key:''})
const roles=[
  {key:'planner',label:'分镜文本模型',hint:'根据商品文字与创作要求编写分镜，使用 OpenAI Chat Completions 协议。此模型不读取商品图片。'},
  {key:'video',label:'视频生成模型',hint:'根据分镜与首帧图片生成视频，支持火山方舟 Seedance 和阿里云百炼万相。'},
  {key:'visual',label:'视觉检查模型',hint:'检查成片中的商品一致性，须使用支持图片输入的 Chat Completions 模型；可选择不检查。'},
] as const
const modelDraft=ref({enabled:true,adapter:'openai_chat' as VideoAdapter,base_url:'',model:'',api_key:'',max_segment_seconds:'' as number|string})
const activeRole=computed(()=>roles.find(role=>role.key===open.value))
const savedModel=computed(()=>activeRole.value?models.value?.models[activeRole.value.key]:null)
const needsModelKey=computed(()=>!savedModel.value?.has_api_key || !savedModel.value.enabled ||
  savedModel.value.adapter!==modelDraft.value.adapter || savedModel.value.base_url!==modelDraft.value.base_url.trim().replace(/\/$/,''))
const needsServiceKey=computed(()=>!connection.value?.has_service_key || connectionDraft.value.base_url.replace(/\/$/,'')!==connection.value.base_url)
const providerHint=computed(()=>modelDraft.value.adapter==='wan'
  ?'地址填到业务空间的 /api/v1，例如 https://llm-xxx.cn-beijing.maas.aliyuncs.com/api/v1；模型名例如 wan2.2-i2v-flash 或 wan3.0-video。'
  :'地址例如 https://ark.cn-beijing.volces.com/api/v3；模型名或推理接入点从方舟控制台复制。')
const title=computed(()=>open.value==='connection'?'配置视频服务连接':open.value==='sound'?'视频声音设置':'配置'+(activeRole.value?.label??''))
function clearKeys(){connectionDraft.value.service_key='';connectionDraft.value.management_key='';modelDraft.value.api_key=''}
function close(value:boolean){if(!value&&!busy.value){open.value=null;clearKeys()}}
async function initialize(){
  const loaded=await run(()=>api.getMediaConnection('video'),latest=>{
    connection.value=latest;models.value=null;runtimeSummary.value=null
  })
  if(!loaded||!connection.value?.has_service_key)return
  await run(async()=>({value:await api.getVideoModels(),settings:await api.getMediaResource('video','settings')}),
    ({value,settings})=>{models.value=value;runtimeSummary.value=settings??null})
}
async function configureConnection(){if(busy.value)return;conflict.value=false;notice.value=''
  await run(()=>api.getMediaConnection('video'),value=>{connection.value=value;
    connectionDraft.value={base_url:value.base_url??'',service_key:'',management_key:''};open.value='connection'})}
async function configureModel(role:VideoModelRole){if(busy.value)return;conflict.value=false;notice.value=''
  await run(()=>api.getVideoModels(),value=>{models.value=value;const saved=value.models[role];
    modelDraft.value={enabled:role!=='visual'||!!saved?.enabled,adapter:saved?.adapter??(role==='planner'?'openai_chat':role==='visual'?'openai_vision':'seedance'),
      base_url:saved?.base_url??'',model:saved?.model??'',api_key:'',max_segment_seconds:saved?.max_segment_seconds??''};open.value=role})}
async function saveConnection(){if(!connection.value||conflict.value)return
  const ok=await run(async()=>{try{return await api.saveMediaConnection('video',{
    expected_revision:connection.value!.revision,base_url:connectionDraft.value.base_url,
    ...(connectionDraft.value.service_key?{service_key:connectionDraft.value.service_key}:{}),
    ...(connectionDraft.value.management_key?{management_key:connectionDraft.value.management_key}:{})})}
    catch(e){if(e instanceof ApiError&&e.status===409)conflict.value=true;throw e}},
    value=>{connection.value=value;models.value=null;open.value=null;clearKeys();notice.value='服务连接已保存。'})
  if(ok)await initialize()}
async function configureSound(){if(busy.value)return;conflict.value=false;notice.value=''
  await run(async()=>({audio:await api.getVideoAudio(),value:await api.getVideoModels()}),({audio,value})=>{
    sound.value=audio;soundDraft.value=audio.enabled;models.value=value;open.value='sound'})}
async function saveSound(){if(!models.value||conflict.value)return
  await run(async()=>{try{return await api.saveVideoAudio({expected_revision:sound.value.revision,
    expected_configuration_revision:models.value!.configuration_revision,enabled:soundDraft.value})}
    catch(e){if(e instanceof ApiError&&e.status===409)conflict.value=true;throw e}},value=>{
    sound.value=value;open.value=null;notice.value='声音设置已保存。'})
  if(!open.value)await initialize()}
async function saveModel(){if(!models.value||!activeRole.value||conflict.value)return
  const role=activeRole.value.key,saved=savedModel.value,value=modelDraft.value
  await run(async()=>{try{
    if(value.enabled&&needsModelKey.value&&!value.api_key)throw new Error('首次配置或更换 API 地址、供应商时，请填写 API Key。')
    if(value.enabled&&(!value.base_url.trim()||!value.model.trim()))throw new Error('请填写 API 地址和模型名称。')
    if(value.enabled&&value.adapter==='wan'&&(!Number.isInteger(Number(value.max_segment_seconds))||Number(value.max_segment_seconds)<1||Number(value.max_segment_seconds)>15))throw new Error('单段最长秒数须为 1–15 的整数。')
    const body:VideoModelWrite={expected_revision:models.value!.revision,expected_configuration_revision:models.value!.configuration_revision,
      expected_profile_id:saved?.profile_id??null,expected_profile_version:saved?.version??null,enabled:value.enabled,adapter:value.adapter,
      ...(value.enabled?{base_url:value.base_url.trim(),model:value.model.trim(),...(value.api_key?{api_key:value.api_key}:{}),
        ...(value.adapter==='wan'?{max_segment_seconds:Number(value.max_segment_seconds)}:{})}:{})}
    return await api.saveVideoModel(role,body)
  }catch(e){if(e instanceof ApiError&&e.status===409)conflict.value=true;throw e}},
  result=>{models.value=result;open.value=null;clearKeys();notice.value='模型配置已保存。'})}
function runtimeSaved(){runtime.value=false;notice.value='运行设置已保存。';void initialize()}
onBeforeUnmount(clearKeys)
onMounted(initialize)
</script>

<template>
  <section class="panel">
    <div class="section-heading"><h2>视频服务连接</h2><UiButton type="button" class="button" data-configure-connection :aria-disabled="busy" @click="configureConnection">配置服务连接</UiButton></div>
    <p v-if="connection">{{ connection.base_url||'尚未设置服务地址' }} · {{ connection.has_service_key?'访问 Key 已配置':'访问 Key 未配置' }}<template v-if="connection.has_management_key"> · 管理 Key 已配置</template></p>
  </section>
  <section class="panel" :aria-busy="busy">
    <div class="section-heading"><div><h2>视频模型配置</h2><p class="field-hint">按实际用途配置，保存后自动接入对应环节。</p></div><div class="settings-actions"><UiButton type="button" class="button" :disabled="!connection?.has_service_key" :aria-disabled="busy||!connection?.has_service_key" @click="configureSound">声音设置</UiButton><UiButton type="button" class="button" :disabled="!connection?.has_service_key" :aria-disabled="busy||!connection?.has_service_key" @click="!busy&&(runtime=true)">运行设置</UiButton></div></div>
    <p v-if="busy&&!open" role="status">正在读取配置…</p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="runtimeSummary?.mode" class="field-hint">当前出片方式：{{ runtimeSummary.mode==='real'?'真实模型':'替身测试' }} · 默认成片 {{ runtimeSummary.default_duration }} 秒</p>
    <p v-if="error&&!open" class="field-error" role="alert">{{ error }} <UiButton type="button" class="button" :disabled="busy" @click="initialize">重新读取</UiButton></p>
    <p v-if="connection&&!connection.has_service_key">请先配置 videoAgent 服务连接，再配置模型。</p>
    <div v-else-if="models" class="video-models">
      <article v-for="role in roles" :key="role.key" class="video-model">
        <div class="section-heading"><h3>{{ role.label }}</h3><UiButton type="button" class="button" :data-configure-planner="role.key==='planner'?true:undefined" :data-configure-video="role.key==='video'?true:undefined" :data-configure-visual="role.key==='visual'?true:undefined" :aria-disabled="busy" @click="configureModel(role.key)">配置模型</UiButton></div>
        <p class="model-name">{{ models.models[role.key]?.model||(role.key==='visual'?'不检查':'尚未配置') }}</p>
        <p v-if="models.models[role.key]" class="model-address">{{ models.models[role.key]!.base_url }}</p>
        <p v-if="models.models[role.key]" class="field-hint">{{ models.models[role.key]!.adapter==='wan'?'阿里云百炼万相':models.models[role.key]!.adapter==='seedance'?'火山方舟 Seedance':'OpenAI Chat Completions' }} · {{ models.models[role.key]!.has_api_key?'密钥已配置':'密钥未配置' }}<template v-if="models.models[role.key]!.adapter==='wan'"> · 单段最长 {{ models.models[role.key]!.max_segment_seconds }} 秒</template></p>
        <p class="field-hint">{{ role.hint }}</p>
      </article>
    </div>
  </section>
  <AppDrawer :open="open!==null" :title="title" purpose="edit" @update:open="close">
    <form v-if="open==='connection'" id="video-connection-form" class="form-stack" @submit.prevent="saveConnection">
      <fieldset class="form-stack" :disabled="busy">
        <label for="media-service-url">服务地址<UiInput id="media-service-url" v-model="connectionDraft.base_url" type="url" data-initial-focus required maxlength="2048" aria-describedby="video-service-help" /></label>
        <small id="video-service-help">填写 videoAgent 的 HTTP(S) 服务地址，不含接口路径。更换地址需填写新的访问 Key。</small>
        <label for="media-service-key">{{ needsServiceKey?'服务访问 Key':'替换服务访问 Key（留空保留）' }}<UiInput id="media-service-key" v-model="connectionDraft.service_key" type="password" autocomplete="new-password" :required="needsServiceKey" maxlength="8192" /></label>
        <label for="media-management-key">管理访问 Key（留空保留）<UiInput id="media-management-key" v-model="connectionDraft.management_key" type="password" autocomplete="new-password" :required="needsServiceKey&&!!connection?.has_management_key" maxlength="8192" /></label>
        <small>管理 Key 用于读取和保存 videoAgent 配置；未单独设置时使用服务访问 Key。更换地址时，已配置的管理 Key 也需重新填写。</small>
      </fieldset>
    </form>
    <form v-else-if="open==='sound'" id="video-sound-form" class="form-stack" @submit.prevent="saveSound">
      <fieldset class="form-stack" :disabled="busy"><label for="video-sound-enabled">成片声音<UiSelect id="video-sound-enabled" v-model="soundDraft" aria-label="成片声音" data-initial-focus><option :value="false">无声</option><option :value="true">有声</option></UiSelect></label>
      <p class="field-hint">有声时向所选视频供应商请求音轨；供应商不支持时，由 videoAgent 补充本地占位声音。当前没有独立的真实配音、音乐模型接口。替身测试也使用本地占位声音。</p>
      <p class="field-hint">保存后用于新提交的任务，已受理任务保留原声音设置；生成前仍需确认视频方案。</p></fieldset>
    </form>
    <form v-else-if="activeRole" id="video-model-form" class="form-stack" @submit.prevent="saveModel">
      <fieldset class="form-stack" :disabled="busy">
        <p id="video-model-help" class="field-hint">{{ activeRole.hint }}</p>
        <label v-if="open==='visual'" for="video-visual-enabled">检查方式<UiSelect id="video-visual-enabled" v-model="modelDraft.enabled" aria-label="检查方式" data-initial-focus><option :value="false">不检查</option><option :value="true">调用视觉模型检查</option></UiSelect></label>
        <template v-if="modelDraft.enabled">
          <label v-if="open==='video'" for="video-provider">视频供应商<UiSelect id="video-provider" v-model="modelDraft.adapter" aria-label="视频供应商" data-initial-focus @change="modelDraft.api_key=''">
            <option value="seedance">火山方舟 Seedance</option><option value="wan">阿里云百炼万相</option></UiSelect></label>
          <p v-if="open==='video'" id="video-provider-help" class="field-hint">{{ providerHint }}</p>
          <label for="video-model-url">API 地址<UiInput id="video-model-url" v-model="modelDraft.base_url" type="url" :data-initial-focus="open==='planner'?true:undefined" required maxlength="2000" :aria-describedby="open==='video'?'video-provider-help':'video-model-help'" /></label>
          <label for="video-model-name">模型名称<UiInput id="video-model-name" v-model="modelDraft.model" required maxlength="200" /></label>
          <label for="video-model-key">{{ needsModelKey?'API Key':'替换 API Key（留空保留）' }}<UiInput id="video-model-key" v-model="modelDraft.api_key" type="password" autocomplete="new-password" :required="needsModelKey" maxlength="8192" /></label>
          <label v-if="modelDraft.adapter==='wan'" for="video-segment-seconds">单段最长秒数<UiInput id="video-segment-seconds" v-model.number="modelDraft.max_segment_seconds" type="number" min="1" max="15" step="1" required aria-describedby="video-segment-help" /></label>
          <small v-if="modelDraft.adapter==='wan'" id="video-segment-help">填写该模型单次生成的实际时长上限（1–15 秒）。更长的成片由 videoAgent 拆分为多段。</small>
        </template>
      </fieldset>
    </form>
    <p v-if="error&&open" class="field-error" role="alert">{{ error }}</p>
    <p v-if="conflict" class="field-hint">草稿已保留，请关闭后重新打开编辑。</p>
    <template #actions><UiButton class="button primary" :form="open==='connection'?'video-connection-form':open==='sound'?'video-sound-form':'video-model-form'" :data-save-connection="open==='connection'?true:undefined" :data-save-video-model="activeRole?true:undefined" :disabled="busy||conflict">{{ open==='connection'?'保存服务连接':open==='sound'?'保存声音设置':'保存模型配置' }}</UiButton></template>
  </AppDrawer>
  <VideoRuntimeSettings v-if="runtime" @closed="runtime=false" @saved="runtimeSaved" />
</template>

<style scoped>
.settings-actions{display:flex;flex-wrap:wrap;gap:8px}
.video-models{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}.video-model{min-width:0;border-top:1px solid var(--color-border);padding-top:20px}.video-model .section-heading{align-items:flex-start;gap:12px}.video-model h3{margin:0;font-size:16px}.video-model p{overflow-wrap:anywhere}.model-name{font-weight:600;margin-bottom:6px}.model-address{font-size:13px;color:var(--color-muted);margin-top:0}fieldset{min-width:0;border:0;padding:0;margin:0}@media(max-width:1050px){.video-models{grid-template-columns:1fr;gap:16px}.video-model{padding-top:16px}}
</style>
