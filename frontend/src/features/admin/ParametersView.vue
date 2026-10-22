<script setup lang="ts">
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import { onMounted, ref } from 'vue'
import * as api from '../../api/admin'
import type { Schema } from '../../types/api'
import AppDrawer from '../../components/AppDrawer.vue'
import { useAdminRequest } from './shared'
const { busy, error, run } = useAdminRequest()
const current = ref<Schema<'ParameterConfigView'> | null>(null), open = ref(false), notice = ref('')
const draft = ref({ text_price: '', image_price: '', video_price: '' })
const expectedVersion = ref<string | null>(null)
const fields = [{ key: 'text_price', id: 'text-price', label: '文本价格' }, { key: 'image_price', id: 'image-price', label: '图片价格' }, { key: 'video_price', id: 'video-price', label: '视频价格' }] as const
function load() { return run(api.getParameterConfig, value => { current.value = value }) }
async function edit() {
  if (!await load() || !current.value) return
  expectedVersion.value = current.value.version
  for (const {key} of fields) draft.value[key] = current.value[key]?.toString() ?? ''
  error.value = ''; open.value = true
}
async function save() {
  const values: Record<string, number | null> = {}
  for (const {key, label} of fields) {
    const value = String(draft.value[key]).trim()
    if (value && (!/^\d+$/.test(value) || !Number.isSafeInteger(Number(value)))) { error.value = label + '须为 0 至 9007199254740991 的整数。'; return }
    values[key] = value === '' ? null : Number(value)
  }
  // Omit hidden assist fields so the server preserves the existing connection.
  await run(() => api.saveParameterConfig({ expected_version: expectedVersion.value, ...values } as Schema<'ParameterConfigUpdate'>), value => { current.value = value; open.value = false; notice.value = '参数已保存。新创作使用当前价格。' })
}
onMounted(load)
</script>
<template>
  <div class="admin-page">
    <p v-if="error && !open" class="field-error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
    <section class="panel"><div class="section-heading"><h2>创作价格</h2><div class="action-row"><UiButton class="button" :disabled="busy" @click="load">刷新参数</UiButton><UiButton class="button primary" :disabled="busy || !current" @click="edit">编辑参数</UiButton></div></div>
      <dl v-if="current" class="detail-list"><template v-for="field in fields" :key="field.key"><dt>{{ field.label }}</dt><dd>{{ current[field.key] === null ? '未配置' : current[field.key] + ' 积分 / 次' }}</dd></template></dl><p v-else role="status">{{ busy ? '正在读取参数…' : '暂时无法读取参数。' }}</p><p>未配置价格时无法生成；0 表示本次不收取积分。</p>
    </section>
  </div>
  <AppDrawer v-model:open="open" title="编辑参数配置" purpose="edit" class="admin-overlay">
    <form id="parameter-form" class="form-stack" @submit.prevent="save"><h3>创作价格</h3><p>单位：积分 / 次。留空表示未配置。</p><label v-for="(field, index) in fields" :key="field.key" :for="field.id">{{ field.label }}<UiInput :id="field.id" v-model="draft[field.key]" type="number" min="0" max="9007199254740991" step="1" :data-initial-focus="index === 0 ? '' : undefined" /></label><p>保存后，新提交将使用最新价格，已受理任务保留原费用。</p>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p></form>
    <template #actions><UiButton class="button primary" type="submit" form="parameter-form" :disabled="busy">保存参数</UiButton></template>
  </AppDrawer>
</template>
