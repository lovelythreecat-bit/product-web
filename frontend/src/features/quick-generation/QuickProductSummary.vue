<script setup lang="ts">
import { MAX_PRODUCT_REFERENCES } from '../workspace/materialLimits'
import { computed, ref, watch } from 'vue'
import type { Schema } from '../../types/api'
import UiButton from '../../components/ui/UiButton.vue'
import AppDialog from '../../components/AppDialog.vue'
import { fileContentUrl } from '../../api/files'
import { editableProduct, longProductFields, productFormGroups } from '../workspace/productTypes'
import { labeledEntries } from '../workspace/display'

const props = defineProps<{
  product: Schema<'ProductVersionView'> | null
  materials: Schema<'FileVersionRef'>[]
  disabled: boolean
  readOnly?: boolean
  uploading: boolean
}>()
const emit = defineEmits<{ edit: []; upload: []; dropFiles: [files: File[]]; remove: [index: number] }>()
const dragDepth = ref(0)
const dropError = ref('')
const selectedId = ref(''), previewOpen = ref(false)
const selectedIndex = computed(() => Math.max(0, props.materials.findIndex(item => item.file_id === selectedId.value)))
const selected = computed(() => props.materials[selectedIndex.value])
watch(() => props.materials.map(item => item.file_id), (ids, previous = []) => {
  if (!ids.includes(selectedId.value)) selectedId.value = ids[Math.min(Math.max(0, previous.indexOf(selectedId.value)), ids.length - 1)] || ''
  if (!ids.length) previewOpen.value = false
}, { immediate: true })
function selectReference(index: number) {
  selectedId.value = props.materials[index]?.file_id || ''
  if (window.matchMedia?.('(max-width: 600px)').matches) previewOpen.value = true
}
function browseReference(delta: number) {
  const count = props.materials.length
  if (count) selectedId.value = props.materials[(selectedIndex.value + delta + count) % count]!.file_id
}
const canUpload = computed(() => !props.readOnly && !props.disabled && !props.uploading && props.materials.length < MAX_PRODUCT_REFERENCES)
function dragEnter(event: DragEvent) {
  if (canUpload.value && event.dataTransfer?.types.includes('Files')) dragDepth.value++
}
function dragOver(event: DragEvent) {
  if (event.dataTransfer) event.dataTransfer.dropEffect = canUpload.value ? 'copy' : 'none'
}
function dropFiles(event: DragEvent) {
  dragDepth.value = 0
  if (!canUpload.value) return
  const files = Array.from(event.dataTransfer?.files || [])
  if (!files.length) return
  if (files.some(file => !['image/png', 'image/jpeg', 'image/webp'].includes(file.type))) {
    dropError.value = '请上传 PNG、JPG 或 WebP 图片。'
    return
  }
  if (files.length + props.materials.length > MAX_PRODUCT_REFERENCES) {
    dropError.value = `最多上传 ${MAX_PRODUCT_REFERENCES} 张图片，还可以添加 ${Math.max(0, MAX_PRODUCT_REFERENCES - props.materials.length)} 张。`
    return
  }
  dropError.value = ''
  emit('dropFiles', files)
}
const groups = computed(() => {
  const entries = labeledEntries(editableProduct(props.product?.product || {}), 'product')
    .filter(entry => !['name', 'category'].includes(entry.key))
  const definitions = productFormGroups(props.product?.product.product_type)
  const assigned = new Set(definitions.flatMap(group => group.fields))
  return [...definitions, { title: '已有补充资料', fields: entries.filter(entry => !assigned.has(entry.key)).map(entry => entry.key) }]
    .map(group => ({ title: group.title, entries: entries.filter(entry => group.fields.includes(entry.key)) }))
    .filter(group => group.entries.length)
})
</script>

<template>
  <section class="quick-product-sheet" aria-label="商品资料">
    <section class="quick-product-references" :class="{ 'is-dragging': dragDepth > 0, 'is-empty': !materials.length }" aria-label="商品参考图片" :aria-busy="uploading" @dragenter.prevent="dragEnter" @dragover.prevent="dragOver" @dragleave.prevent="dragDepth = Math.max(0, dragDepth - 1)" @drop.prevent="dropFiles">
      <h4>商品图片 <small>{{ materials.length }} / {{ MAX_PRODUCT_REFERENCES }}</small></h4>
      <button v-if="selected" type="button" class="quick-reference-feature" aria-label="放大当前商品参考图" @click="previewOpen = true"><img :src="fileContentUrl(selected.file_id)" :alt="'商品参考图 ' + (selectedIndex + 1)"/><span>{{ selectedIndex + 1 }} / {{ materials.length }}</span><span class="quick-reference-zoom" aria-hidden="true">放大</span></button>
      <div class="quick-materials">
        <div v-for="(material, index) in materials" :key="material.file_id" class="quick-material" :class="{ selected: selectedIndex === index }">
          <button type="button" class="quick-reference-select" :data-reference-index="index" :aria-label="'查看商品参考图 ' + (index + 1)" :aria-pressed="selectedIndex === index" @click="selectReference(index)"><img :src="fileContentUrl(material.file_id)" :alt="'商品参考图 ' + (index + 1)"/></button>
          <UiButton v-if="!readOnly" type="button" class="quick-remove" :aria-label="'移除商品参考图 ' + (index + 1)" :disabled="disabled || uploading" @click="emit('remove', index)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6"/></svg></UiButton>
        </div>
        <UiButton v-if="!readOnly" class="button quick-upload" type="button" :disabled="!canUpload" @click="dropError = ''; emit('upload')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>{{ uploading ? '正在上传…' : '上传图片' }}</UiButton>
      </div>
      <p v-if="!readOnly" class="quick-drop-hint">{{ dragDepth > 0 ? '松开即可上传' : '支持拖入图片 · PNG / JPG / WebP' }}</p>
      <p v-else-if="!materials.length" class="quick-drop-hint">暂无参考图片</p>
      <p v-if="dropError" role="alert" class="field-error">{{ dropError }}</p>
    </section>
    <div class="quick-product-information">
    <header class="quick-product-sheet-heading">
      <h3>商品资料</h3>
      <UiButton v-if="!readOnly && !$slots.editor" class="button text-button" type="button" :disabled="disabled" @click="emit('edit')">{{ product ? '编辑资料' : '填写资料' }}</UiButton>
    </header>
    <slot name="editor">
    <template v-if="product">
      <div class="quick-product-identity">
        <div><h3>{{ product.product.name }}</h3><p v-if="product.product.category"><span>商品分类</span>{{ product.product.category }}</p></div>
      </div>
      <section v-for="group in groups" :key="group.title" class="quick-product-facts">
        <h4>{{ group.title }}</h4>
        <dl>
          <div v-for="entry in group.entries" :key="entry.key" :class="{ wide: longProductFields.includes(entry.key) || entry.value.length > 60 }">
            <dt>{{ entry.label }}</dt><dd>{{ entry.value }}</dd>
          </div>
        </dl>
      </section>
    </template>
    <div v-else class="quick-product-empty"><p>添加商品资料，让这次创作更贴合商品。</p><UiButton v-if="!readOnly" class="button" type="button" :disabled="disabled" @click="emit('edit')">填写商品资料</UiButton></div>
    </slot>
    </div>
  </section>
  <AppDialog v-model:open="previewOpen" title="商品参考图"><img v-if="selected && previewOpen" data-reference-preview class="quick-reference-preview" :src="fileContentUrl(selected.file_id)" :alt="'商品参考图 ' + (selectedIndex + 1)"/><template #actions><UiButton class="button" data-reference-previous :disabled="materials.length < 2" @click="browseReference(-1)">上一张</UiButton><span>{{ selectedIndex + 1 }} / {{ materials.length }}</span><UiButton class="button" data-reference-next :disabled="materials.length < 2" @click="browseReference(1)">下一张</UiButton></template></AppDialog>
</template>

<style scoped>
.quick-product-sheet { display:grid; grid-template-columns:minmax(200px, .38fr) minmax(0, 1fr); gap:28px; min-width:0 }
.quick-product-information { min-width:0 }
.quick-product-sheet-heading { display:flex; align-items:center; justify-content:space-between; gap:16px; min-height:32px; margin-bottom:12px }
.quick-product-sheet-heading h3 { font-size:14px; font-weight:600 }
.quick-product-identity { padding:0 0 16px }
.quick-product-identity>div { min-width:0 }
.quick-product-identity h3 { font-size:22px; font-weight:600; line-height:1.5; overflow-wrap:anywhere }
.quick-product-identity p { display:flex; flex-wrap:wrap; gap:6px 12px; margin:6px 0 0; font-size:13px }
.quick-product-identity p span { color:var(--color-muted) }
.quick-product-facts { padding:12px 0; border-top:1px solid var(--color-border) }
.quick-product-sheet h4 { margin:0 0 10px; font-size:13px; font-weight:600; color:var(--color-text) }
.quick-product-facts dl { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 24px; margin:0; font-size:13px; line-height:1.8 }
.quick-product-facts dl>div { display:grid; grid-template-columns:80px minmax(0,1fr); gap:8px; min-width:0 }
.quick-product-facts .wide { grid-column:1/-1 }
.quick-product-facts dl>div.wide { grid-template-columns:minmax(0,1fr); gap:6px }
.quick-product-facts dt { color:var(--color-muted); overflow-wrap:anywhere }
.quick-product-facts dd { margin:0; white-space:pre-wrap; overflow-wrap:anywhere; color:var(--color-text) }
.quick-product-references { min-width:0; align-self:start; padding:0; border:1px solid transparent; border-radius:12px }
.quick-product-references.is-dragging { border-color:var(--color-primary); background:var(--color-message) }
.quick-product-references h4 { display:flex; align-items:baseline; justify-content:space-between; gap:8px; margin-bottom:12px }
.quick-product-sheet .quick-product-empty { margin:0; padding:20px; background:var(--color-background) }
.quick-product-sheet .quick-materials { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; margin-top:12px }
.quick-product-sheet .quick-material,.quick-product-sheet .quick-upload { width:100%; height:auto; aspect-ratio:1; min-width:0; border-radius:var(--radius-control) }
.quick-product-sheet .quick-material { background:var(--color-panel); border-color:var(--color-border) }
.quick-reference-feature { position:relative; display:block; width:100%; aspect-ratio:1; border:0; padding:0; border-radius:10px; overflow:hidden; background:var(--color-background); cursor:zoom-in }
.quick-reference-feature img,.quick-reference-select img { width:100%; height:100%; object-fit:contain }
.quick-reference-feature span { position:absolute; left:10px; bottom:10px; padding:3px 8px; border-radius:5px; background:var(--color-panel); font-size:12px }
.quick-reference-feature .quick-reference-zoom { left:auto; right:10px }
.quick-reference-select { display:block; width:100%; height:100%; padding:0; border:0; background:var(--color-background); cursor:pointer }
.quick-product-sheet .quick-material { border:2px solid transparent; padding:2px }
.quick-product-sheet .quick-material.selected { border-color:var(--color-primary) }
.quick-reference-preview { display:block; width:100%; max-height:65dvh; object-fit:contain }
.quick-product-sheet .quick-upload { margin:0; color:var(--color-primary); background:var(--color-panel); padding:8px 4px }
.quick-product-references.is-empty .quick-upload { grid-column:1/-1; min-height:180px; aspect-ratio:auto }
.quick-product-sheet .quick-upload :deep(> span) { display:flex; flex-direction:column; align-items:center; gap:4px }
.quick-product-sheet .quick-upload svg { width:20px; height:20px }
.quick-product-sheet .quick-upload:hover:not(:disabled) { border-color:var(--color-primary); background:var(--color-message) }
.quick-drop-hint { font-size:12px; line-height:1.6; color:var(--color-muted); margin:10px 0 0; overflow-wrap:anywhere }
@media(min-width:901px) and (max-width:1200px), (max-width:700px) {
  .quick-product-facts dl { grid-template-columns:minmax(0,1fr) }
}
@media(max-width:700px) {
  .quick-product-sheet { grid-template-columns:minmax(0,1fr); gap:20px }
  .quick-product-sheet .quick-materials { grid-template-columns:repeat(3,minmax(0,1fr)) }
  .quick-product-references.is-empty .quick-upload { min-height:120px }
  .quick-product-sheet-heading { margin-bottom:8px }
  .quick-product-identity h3 { font-size:18px }
  .quick-product-facts dl>div { grid-template-columns:82px minmax(0,1fr); gap:10px }
  .quick-product-sheet .quick-remove { width:44px; height:44px; min-width:44px; min-height:44px; top:0; right:0 }
}
@media(max-width:600px) { .quick-reference-feature { display:none }.quick-product-sheet .quick-material.selected { border-color:transparent } }
@media(pointer:coarse) { .quick-product-sheet .quick-remove { width:44px; height:44px; min-width:44px; min-height:44px } }
</style>
