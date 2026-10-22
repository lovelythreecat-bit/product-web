<script setup lang="ts">
import { computed, onScopeDispose, ref, watch } from 'vue'
import type { Schema } from '../../types/api'
import { createProductVersion } from '../../api/conversations'
import AppDrawer from '../../components/AppDrawer.vue'
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import { editableProduct, longProductFields, productFormGroups, productType, productTypes } from '../workspace/productTypes'
import { fieldLabel, productExamples, productLabels } from '../workspace/display'
const props = defineProps<{ open: boolean; ownerKey: string; product: Schema<'ProductVersionView'> | null; requiredFields: string[]; inline?: boolean; disabled?: boolean; persist?: (value: Schema<'ProductVersionView'>) => Promise<void> }>()
const emit = defineEmits<{ 'update:open': [value: boolean]; saved: [value: Schema<'ProductVersionView'>] }>()
const fields = ref<Record<string, string>>({}), original = ref<Record<string, unknown>>({})
const busy = ref(false), error = ref('')
const baseline = ref('')
const dirty = computed(() => JSON.stringify(fields.value) !== baseline.value)
let alive = true, revision = 0
onScopeDispose(() => { alive = false; revision++ })
watch(() => [props.open, props.ownerKey], () => { revision++ }, { flush: 'sync' })
const groups = computed(() => productFormGroups(fields.value.product_type).map(group => ({ ...group, fields: group.fields.map(field => field === 'description' && props.requiredFields.includes('sellingPoints') && !props.requiredFields.includes('description') ? 'sellingPoints' : field) })))
const extras = computed(() => [...new Set([...Object.keys(original.value), ...props.requiredFields])].filter(key => !groups.value.some(group => group.fields.includes(key))))
function reset() {
  error.value = ''
  original.value = editableProduct(props.product?.product || {}, props.requiredFields)
  fields.value = Object.fromEntries(Object.entries(original.value).map(([k, v]) => [k, typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v ?? '')]))
  baseline.value = JSON.stringify(fields.value)
}
watch(() => [props.open, props.ownerKey], () => { if (props.open) reset() }, { immediate: true })
watch(() => props.product?.version, () => { if (props.open && !busy.value && !dirty.value) reset() })
async function save() {
  if (busy.value || props.disabled) return false
  if (props.inline && props.product && !dirty.value) return true
  const owner = props.ownerKey, stamp = revision
  const type = productType(fields.value.product_type)
  if (!fields.value.name?.trim() || !type) { error.value = '请填写商品名称并选择商品类型。'; return false }
  if (props.requiredFields.some(key => !fields.value[key]?.trim() && key !== 'category')) { error.value = '请填写完整的必填商品资料。'; return false }
  busy.value = true; error.value = ''
  const keys = [...new Set([...groups.value.flatMap(g => g.fields), ...extras.value])]
  const product: Record<string, unknown> = Object.fromEntries(keys.flatMap(key => fields.value[key]?.trim() ? [[key, fields.value[key].trim()]] : []))
  for (const key of keys) if (typeof original.value[key] === 'object' && fields.value[key] === JSON.stringify(original.value[key])) product[key] = original.value[key]
  product.category ||= type.label
  try {
    const value = await createProductVersion({ product: editableProduct(product, props.requiredFields), product_id: props.product?.product_id })
    if (!alive || stamp !== revision || props.ownerKey !== owner || !props.open) return false
    await props.persist?.(value)
    if (!alive || stamp !== revision || props.ownerKey !== owner || !props.open) return false
    baseline.value = JSON.stringify(fields.value)
    emit('saved', value)
    if (!props.inline) emit('update:open', false)
    return true
  }
  catch (cause) { if (alive && stamp === revision) error.value = cause instanceof Error ? cause.message : '资料保存失败，请重试。'; return false }
  finally { busy.value = false }
}
defineExpose({ save, dirty, busy })
</script>
<template>
  <component :is="inline ? 'section' : AppDrawer" :open="inline ? undefined : open" :title="inline ? undefined : '编辑商品资料'" :purpose="inline ? undefined : 'edit'" @update:open="emit('update:open', $event)">
    <form id="quick-product-form" class="form-stack" @submit.prevent="save">
      <fieldset v-for="group in [...groups, ...(extras.length ? [{ title: '已有补充资料', fields: extras }] : [])]" :key="group.title" class="quick-product-group" :disabled="busy || disabled"><legend>{{ group.title }}</legend><div class="quick-product-fields"><div v-for="field in group.fields" :key="field" :class="{ wide: longProductFields.includes(field) }">
        <label :for="'quick-product-' + field">{{ productLabels[field] || fieldLabel(field, 'product', extras.indexOf(field)) }}<small v-if="['name', 'product_type'].includes(field) || requiredFields.includes(field)"> 必填</small></label>
        <UiSelect v-if="field === 'product_type'" :id="'quick-product-' + field" v-model="fields[field]" required :disabled="busy || disabled"><option value="" disabled>请选择商品类型</option><option v-for="type in productTypes" :key="type.value" :value="type.value">{{ type.label }}</option></UiSelect>
        <UiInput v-else :id="'quick-product-' + field" v-model="fields[field]" :type="longProductFields.includes(field) ? 'textarea' : 'text'" :rows="3" :maxlength="longProductFields.includes(field) ? 600 : 120" :placeholder="productExamples[field]" :required="field === 'name' || requiredFields.includes(field)" :disabled="busy || disabled" :data-initial-focus="field === 'name' ? '' : undefined" />
      </div></div></fieldset><p v-if="error" role="alert" class="field-error">{{ error }}</p>
      <div v-if="inline" class="action-row"><UiButton class="button" type="submit" :disabled="busy || disabled || (!!product && !dirty)">{{ busy ? '正在保存…' : '保存商品资料' }}</UiButton></div>
    </form><template #actions><UiButton class="button primary" type="submit" form="quick-product-form" :disabled="busy || disabled">{{ busy ? '正在保存…' : '保存商品资料' }}</UiButton></template>
  </component>
</template>
<style scoped>
.quick-product-group { min-width:0; border:0; border-top:1px solid var(--color-border); margin:0; padding:16px 0 0 }
.quick-product-group legend { padding:0 12px 0 0; font-weight:600 }
.quick-product-fields { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px }
.quick-product-fields>div { min-width:0 }.wide { grid-column:1/-1 }label { display:block; margin-bottom:6px; font-size:13px }small { color:var(--color-primary) }
@media(max-width:400px) { .quick-product-fields { grid-template-columns:minmax(0,1fr) } }
</style>
