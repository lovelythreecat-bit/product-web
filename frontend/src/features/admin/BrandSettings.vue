<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import AppDrawer from '../../components/AppDrawer.vue'
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import { getSiteBrand, updateSiteBrand } from '../../api/site'
import { applyBrand } from '../site/brand'
import type { Schema } from '../../types/api'
import { useAdminRequest } from './shared'

const { busy, error, run } = useAdminRequest()
const current = ref<Schema<'SiteBrandView'> | null>(null)
const open = ref(false), name = ref(''), notice = ref('')
const editButton = ref<InstanceType<typeof UiButton>>()
function load() { return run(getSiteBrand, value => { current.value = value; applyBrand(value) }) }
async function edit() {
  if (!await load() || !current.value) return
  name.value = current.value.name; notice.value = ''
  // Loading temporarily disables the trigger; restore it before the overlay captures focus.
  await nextTick()
  editButton.value?.focus()
  open.value = true
}
async function save() {
  const value = name.value.trim()
  if (!value || [...value].length > 24 || /[\u0000-\u001f\u007f]/.test(value)) {
    error.value = '请输入 1–24 个字符的 Logo 名称，不含换行或控制字符。'; return
  }
  if (!current.value) return
  await run(() => updateSiteBrand({ name: value, expected_version: current.value!.version }), result => {
    current.value = result; applyBrand(result); open.value = false; notice.value = 'Logo 名称已保存。'
  })
}
onMounted(load)
</script>

<template>
  <section class="panel">
    <div class="section-heading"><h2>品牌设置</h2><div class="action-row">
      <UiButton type="button" class="button" :disabled="busy" @click="load">刷新品牌</UiButton>
      <UiButton ref="editButton" type="button" class="button primary" :disabled="busy || !current" @click="edit">编辑 Logo 名称</UiButton>
    </div></div>
    <dl v-if="current" class="detail-list"><dt>Logo 名称</dt><dd>{{ current.name }}</dd></dl>
    <p v-else role="status">{{ busy ? '正在读取品牌设置…' : '暂时无法读取品牌设置。' }}</p>
    <p>用于首页、登录页及各页面导航，保存后统一生效。</p>
    <p v-if="error && !open" class="field-error" role="alert">{{ error }}</p>
    <p v-if="notice" role="status">{{ notice }}</p>
  </section>
  <AppDrawer v-model:open="open" title="编辑 Logo 名称" purpose="edit" class="admin-overlay">
    <form id="brand-form" class="form-stack" @submit.prevent="save">
      <label for="brand-name">Logo 名称<UiInput id="brand-name" v-model="name" required maxlength="24" data-initial-focus aria-describedby="brand-hint brand-error" :aria-invalid="error ? 'true' : undefined" /></label>
      <p id="brand-hint" class="field-hint">1–24 个字符，保存后对所有用户展示。</p>
      <p id="brand-error" class="field-error" role="alert">{{ error }}</p>
    </form>
    <template #actions><UiButton type="submit" class="button primary" form="brand-form" :disabled="busy">{{ busy ? '正在保存…' : '保存名称' }}</UiButton></template>
  </AppDrawer>
</template>
