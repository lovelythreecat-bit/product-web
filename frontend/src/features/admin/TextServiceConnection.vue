<script setup lang="ts">
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import { computed, onMounted, ref } from 'vue'
import * as api from '../../api/admin'
import type { Schema } from '../../types/api'
import { ApiError } from '../../api/client'
import AppDrawer from '../../components/AppDrawer.vue'
import { useAdminRequest } from './shared'

const emit = defineEmits<{ saved: [] }>()
const { busy, error, run } = useAdminRequest()
const connection = ref<Schema<'TextServiceConnectionView'> | null>(null)
const open = ref(false), conflict = ref(false), notice = ref('')
const draft = ref({ base_url: '', service_key: '' })
const needsKey = computed(() => !connection.value?.has_service_key || draft.value.base_url.replace(/\/$/, '') !== connection.value.base_url)
function load() {
  return run(api.getTextServiceConnection, value => { connection.value = value })
}
function edit() {
  if (!connection.value) return
  draft.value = { base_url: connection.value.base_url ?? '', service_key: '' }
  conflict.value = false; error.value = ''; open.value = true
}
async function reloadConflict() {
  if (await load()) edit()
}
async function save() {
  if (!connection.value || conflict.value) return
  await run(async () => {
    try {
      return await api.saveTextServiceConnection({
        expected_revision: connection.value!.revision,
        base_url: draft.value.base_url,
        ...(draft.value.service_key ? { service_key: draft.value.service_key } : {}),
      })
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) conflict.value = true
      throw e
    }
  }, value => {
    connection.value = value; draft.value.service_key = ''; open.value = false
    notice.value = '服务连接已保存。'; emit('saved')
  })
}
onMounted(load)
</script>

<template>
  <section class="panel">
    <div class="section-heading"><h2>服务连接设置</h2><UiButton class="button" :disabled="busy" @click="connection ? edit() : load()">{{ connection ? '配置服务连接' : '重新加载服务连接' }}</UiButton></div>
    <p v-if="connection">{{ connection.base_url || '尚未设置服务地址' }} · {{ connection.has_service_key ? '服务 Key 已配置' : '服务 Key 未配置' }}</p>
    <p v-else-if="busy" role="status">正在加载服务连接…</p>
    <p v-if="error && !open" class="field-error" role="alert">{{ error }}</p>
    <p v-if="notice" role="status">{{ notice }}</p>
  </section>
  <AppDrawer v-model:open="open" class="admin-overlay" title="配置服务连接" purpose="edit" @update:open="value => { if (!value) draft.service_key = '' }">
    <form id="text-service-form" class="form-stack" @submit.prevent="save">
      <label for="text-service-url">服务地址<UiInput id="text-service-url" v-model="draft.base_url" data-initial-focus type="url" maxlength="2048" placeholder="http://127.0.0.1:8000" required aria-describedby="text-service-url-help" /></label>
      <small id="text-service-url-help">填写文本服务的地址，不包含接口路径。</small>
      <label for="text-service-key">{{ needsKey ? '服务访问 Key' : '替换服务访问 Key（留空保留原 Key）' }}<UiInput id="text-service-key" v-model="draft.service_key" type="password" autocomplete="new-password" maxlength="8192" :required="needsKey" aria-describedby="text-service-key-help" /></label>
      <small id="text-service-key-help">使用 textAgent 签发的服务 Key，需要模型配置读写、生成和记录查询权限。</small>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
      <template v-if="conflict"><p>服务连接已改变。当前草稿已保留。</p><UiButton type="button" class="button" :disabled="busy" @click="reloadConflict">放弃草稿并载入最新连接</UiButton></template>
    </form>
    <template #actions><UiButton class="button primary" form="text-service-form" :disabled="busy || conflict">保存服务连接</UiButton></template>
  </AppDrawer>
</template>
