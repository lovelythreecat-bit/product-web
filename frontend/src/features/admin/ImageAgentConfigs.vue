<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import AppDrawer from '../../components/AppDrawer.vue'
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import * as api from '../../api/mediaAgents'
import type { ImageModels, ImageModelWrite, MediaConnection } from '../../api/mediaAgents'
import { ApiError } from '../../api/client'
import { useAdminRequest } from './shared'

const { busy, error, run } = useAdminRequest()
const connection = shallowRef<MediaConnection | null>(null), models = shallowRef<ImageModels | null>(null)
const open = ref<'connection' | 'models' | null>(null), conflict = ref(false), notice = ref('')
const connectionDraft = ref({base_url:'',service_key:''})
const roles = [
  {key:'text_model',id:'text',label:'文字模型',hint:'用于商品图片分析、创作策划和结果审核，需支持图片输入。'},
  {key:'image_model',id:'generation',label:'图片生成模型',hint:'用于生成商品图片。'},
] as const
const blank = (protocol: ImageModelWrite['protocol']): ImageModelWrite => ({base_url:'',model:'',protocol,api_key:''})
const draft = ref({text_model:blank('chat_completions'),image_model:blank('openai_images')})
const needsServiceKey = () => !connection.value?.has_service_key ||
  connectionDraft.value.base_url.replace(/\/$/,'') !== connection.value.base_url
function needsModelKey(role: 'text_model' | 'image_model') {
  const saved=models.value?.[role], value=draft.value[role]
  return !saved?.has_api_key || !saved.enabled || saved.base_url !== value.base_url.replace(/\/$/,'') || saved.protocol !== value.protocol
}
function clearKeys() {
  connectionDraft.value.service_key=''
  draft.value.text_model.api_key='';draft.value.image_model.api_key=''
}
function close(value: boolean) {
  if (!value && !busy.value) { open.value=null;clearKeys() }
}
async function initialize() {
  await run(async()=>{
    const latest=await api.getMediaConnection('image')
    const settings=latest.has_service_key?await api.getImageModels():null
    return {latest,settings}
  },({latest,settings})=>{connection.value=latest;models.value=settings})
}
async function configureConnection() {
  if(busy.value) return
  conflict.value=false;notice.value=''
  await run(()=>api.getMediaConnection('image'),latest=>{
    connection.value=latest;connectionDraft.value={base_url:latest.base_url??'',service_key:''};open.value='connection'
  })
}
async function configureModels() {
  if(busy.value) return
  conflict.value=false;notice.value=''
  await run(()=>api.getImageModels(),latest=>{
    models.value=latest
    for(const {key} of roles) {
      const value=latest[key]
      draft.value[key]=value?{base_url:value.base_url,model:value.model,protocol:value.protocol,api_key:''}:
        blank(key==='text_model'?'chat_completions':'openai_images')
    }
    open.value='models'
  })
}
async function saveConnection() {
  if (!connection.value || conflict.value) return
  const saved=await run(async()=>{
    try {return await api.saveMediaConnection('image',{
      expected_revision:connection.value!.revision,base_url:connectionDraft.value.base_url,
      ...(connectionDraft.value.service_key?{service_key:connectionDraft.value.service_key}:{})})}
    catch(e){if(e instanceof ApiError && e.status===409)conflict.value=true;throw e}
  },value=>{connection.value=value;models.value=null;open.value=null;clearKeys();notice.value='服务连接已保存。'})
  if(saved) await initialize()
}
async function saveModels() {
  if (!models.value || conflict.value) return
  const body=(role:'text_model'|'image_model'):ImageModelWrite=>{
    const value=draft.value[role]
    return {base_url:value.base_url,model:value.model,protocol:value.protocol,
      ...(value.api_key?{api_key:value.api_key}:{})}
  }
  await run(async()=>{
    try{return await api.saveImageModels({expected_revision:models.value!.revision,
      expected_versions:models.value!.versions,text_model:body('text_model'),image_model:body('image_model')})}
    catch(e){if(e instanceof ApiError && e.status===409)conflict.value=true;throw e}
  },value=>{models.value=value;open.value=null;clearKeys();notice.value='图片模型配置已保存。'})
}
onBeforeUnmount(clearKeys)
onMounted(initialize)
</script>

<template>
  <section class="panel">
    <div class="section-heading"><h2>图片服务连接</h2><UiButton type="button" class="button" data-configure-connection :aria-disabled="busy" @click="configureConnection">配置服务连接</UiButton></div>
    <p v-if="connection">{{ connection.base_url || '尚未设置服务地址' }} · {{ connection.has_service_key?'访问 Key 已配置':'访问 Key 未配置' }}</p>
  </section>
  <section class="panel" :aria-busy="busy">
    <div class="section-heading"><h2>图片模型配置</h2><UiButton type="button" class="button primary" data-configure-image-models :disabled="!connection?.has_service_key" :aria-disabled="busy || !connection?.has_service_key" @click="configureModels">配置模型</UiButton></div>
    <p v-if="busy && !open" role="status">正在读取配置…</p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="error && !open" class="field-error" role="alert">{{ error }}<UiButton type="button" class="button" :disabled="busy" @click="initialize">重新读取</UiButton></p>
    <p v-if="connection && !connection.has_service_key">请先配置 imageAgent 服务连接，再配置两类模型。</p>
    <dl v-else-if="models" class="model-summary">
      <template v-for="role in roles" :key="role.key">
        <dt>{{ role.label }}</dt><dd><strong>{{ models?.[role.key]?.model || '未配置' }}</strong>
          <span v-if="models?.[role.key]">{{ models[role.key]!.base_url }}</span>
          <small v-if="models?.[role.key]">{{ models[role.key]!.enabled?'启用':'停用' }} · {{ models[role.key]!.has_api_key?'密钥已配置':'密钥未配置' }}</small>
          <small>{{ role.hint }}</small>
        </dd>
      </template>
    </dl>
  </section>
  <AppDrawer :open="open==='connection'" title="配置服务连接" purpose="edit" @update:open="close">
    <form id="image-connection-form" class="form-stack" @submit.prevent="saveConnection">
      <fieldset class="form-stack" :disabled="busy">
        <label for="media-service-url">服务地址<UiInput id="media-service-url" v-model="connectionDraft.base_url" type="url" data-initial-focus required maxlength="2048" aria-describedby="image-service-help" /></label>
        <small id="image-service-help">填写 imageAgent 的 HTTP(S) 服务地址，不含接口路径。更换地址需要新的访问 Key。</small>
        <label for="media-service-key">{{ needsServiceKey()?'服务访问 Key':'替换服务访问 Key（留空保留）' }}<UiInput id="media-service-key" v-model="connectionDraft.service_key" type="password" autocomplete="new-password" :required="needsServiceKey()" maxlength="8192" /></label>
      </fieldset>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
    </form>
    <template #actions><UiButton class="button primary" form="image-connection-form" :disabled="busy || conflict">保存服务连接</UiButton></template>
  </AppDrawer>
  <AppDrawer :open="open==='models'" title="配置图片模型" purpose="edit" @update:open="close">
    <form id="image-models-form" class="form-stack" @submit.prevent="saveModels">
      <fieldset v-for="role in roles" :key="role.key" class="form-stack model-fields" :disabled="busy">
        <legend>{{ role.label }}</legend><p :id="'image-'+role.id+'-help'" class="field-hint">{{ role.hint }}</p>
        <label :for="'image-'+role.id+'-url'">API 地址<UiInput :id="'image-'+role.id+'-url'" v-model="draft[role.key].base_url" type="url" :data-initial-focus="role.key==='text_model'?true:undefined" required maxlength="2048" :aria-describedby="'image-'+role.id+'-help'" /></label>
        <label :for="'image-'+role.id+'-model'">模型名称<UiInput :id="'image-'+role.id+'-model'" v-model="draft[role.key].model" required maxlength="300" /></label>
        <label v-if="role.key==='image_model'" for="image-generation-protocol">调用协议<UiSelect id="image-generation-protocol" v-model="draft.image_model.protocol" aria-label="调用协议"><option value="openai_images">OpenAI Images</option><option value="openrouter_images">OpenRouter Images</option></UiSelect></label>
        <label :for="'image-'+role.id+'-key'">{{ needsModelKey(role.key)?'API Key':'替换 API Key（留空保留）' }}<UiInput :id="'image-'+role.id+'-key'" v-model="draft[role.key].api_key" type="password" autocomplete="new-password" :required="needsModelKey(role.key)" maxlength="8192" /></label>
      </fieldset>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
    </form>
    <template #actions><UiButton class="button primary" form="image-models-form" data-save-image-models :disabled="busy || conflict">保存模型配置</UiButton></template>
  </AppDrawer>
</template>

<style scoped>
.model-summary{display:grid;grid-template-columns:112px minmax(0,1fr);gap:24px 16px;margin:0}.model-summary dt{font-weight:600}.model-summary dd{margin:0;display:grid;gap:6px;overflow-wrap:anywhere}.model-summary small{color:var(--color-muted)}fieldset{min-width:0;border:0;padding:0;margin:0}.model-fields+ .model-fields{border-top:1px solid var(--color-border);padding-top:24px}legend{font-size:16px;font-weight:600;margin-bottom:12px}.model-fields p{margin:0}@media(max-width:600px){.model-summary{grid-template-columns:minmax(0,1fr);gap:8px}.model-summary dd+dt{margin-top:16px}}
</style>
