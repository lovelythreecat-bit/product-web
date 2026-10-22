<script setup lang="ts">
import UiButton from './ui/UiButton.vue'
import { ElDropdown, ElDropdownMenu, ElDropdownItem } from 'element-plus/es/components/dropdown/index'
import { computed, ref, watch } from 'vue'
import type { Schema } from '../types/api'
import { fileContentUrl } from '../api/files'
import AppDialog from './AppDialog.vue'
const props = defineProps<{ work: Schema<'WorkView'>; compact?: boolean; showLabels?: boolean; documentLayout?: boolean; galleryLayout?: boolean; hideCopyFileActions?: boolean }>()
const preview = ref(false), feedback = ref(''), previewIndex = ref(0)
const selectedItem = computed(() => props.work.items[previewIndex.value])
function openPreview(index = 0) { previewIndex.value = index; preview.value = true }
function movePreview(step: number) { previewIndex.value = Math.max(0, Math.min(props.work.items.length - 1, previewIndex.value + step)) }
watch(() => [props.work.work_id, props.work.kind, ...props.work.items.map(item => item.file_id)].join(':'), () => { preview.value = false; previewIndex.value = 0; feedback.value = '' }, { flush: 'sync' })
async function copy(text: string) { try { await navigator.clipboard.writeText(text); feedback.value = '已复制完整文案' } catch { feedback.value = '无法自动复制，请选择文案复制。' } }
function download(command: number | 'all') {
  const extension = props.work.kind === 'copy' ? '.txt' : props.work.kind === 'image' ? '.png' : '.mp4'
  props.work.items.forEach((item, index) => {
    if (command !== 'all' && command !== index) return
    const link = document.createElement('a')
    link.href = fileContentUrl(item.file_id)
    link.download = `${props.work.work_id}-${index + 1}${extension}`
    document.body.append(link)
    link.click()
    link.remove()
  })
}
function downloadLabel(index: number) {
  const ordinal = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十'][index] ?? String(index + 1)
  return `下载第${ordinal}${props.work.kind === 'image' ? '张' : '个'}`
}
</script>
<template>
  <div class="result-viewer" :class="{ compact, 'gallery-layout': galleryLayout }">
    <template v-if="galleryLayout">
      <div class="result-body" role="region" tabindex="0" :aria-label="work.kind === 'copy' ? '完整文案内容' : work.kind === 'image' ? '完整图片内容' : '完整视频内容'">
        <div v-for="(item, index) in work.items" :key="item.file_id" class="result-item">
          <h4 v-if="showLabels || work.items.length > 1" class="result-label">{{ work.kind === 'image' ? '图片' : work.kind === 'video' ? '视频' : '文案' }} {{ index + 1 }}</h4>
          <pre v-if="work.kind === 'copy'" class="copy-result">{{ item.text }}</pre>
          <img v-else-if="work.kind === 'image'" :src="fileContentUrl(item.file_id)" :alt="'完整生成作品 ' + (index + 1)" loading="eager" role="button" tabindex="0" aria-haspopup="dialog" :aria-label="'放大图片 ' + (index + 1)" @click="openPreview(index)" @keydown.enter.prevent="openPreview(index)" @keydown.space.prevent="openPreview(index)" />
          <video v-else :src="fileContentUrl(item.file_id)" controls preload="metadata" playsinline />
        </div>
        <p v-if="!work.items.length" class="field-hint">暂无可展示的完整成果，请重新读取作品。</p>
      </div>
      <div class="action-row result-actions">
        <UiButton v-if="work.items.length && !(hideCopyFileActions && work.kind === 'copy')" class="button" type="button" @click="openPreview()">预览</UiButton>
        <template v-for="(item, index) in work.items" :key="item.file_id">
          <UiButton v-if="work.kind === 'copy' && item.text !== null" class="button copy-action" type="button" @click="copy(item.text)">{{ work.items.length > 1 ? '复制文案 ' + (index + 1) : '复制文案' }}</UiButton>
          <a v-if="work.items.length === 1 && !(hideCopyFileActions && work.kind === 'copy')" class="button" :href="fileContentUrl(item.file_id)" :download="work.work_id + (work.kind === 'copy' ? '.txt' : work.kind === 'image' ? '.png' : '.mp4')">下载</a>
        </template>
        <ElDropdown v-if="work.items.length > 1 && !(hideCopyFileActions && work.kind === 'copy')" class="result-download-menu" :trigger="['hover', 'click']" placement="bottom-start" :show-timeout="100" :hide-timeout="150" @command="download">
          <UiButton class="button" type="button">下载<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m5 7.5 5 5 5-5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg></UiButton>
          <template #dropdown><ElDropdownMenu class="result-download-options">
            <ElDropdownItem v-for="(item, index) in work.items" :key="item.file_id" :command="index">{{ downloadLabel(index) }}</ElDropdownItem>
            <ElDropdownItem divided command="all">下载全部</ElDropdownItem>
          </ElDropdownMenu></template>
        </ElDropdown>
        <slot name="actions" />
      </div>
    </template>
    <template v-else>
    <div v-for="(item, index) in work.items" :key="item.file_id" class="result-item">
      <h4 v-if="showLabels" class="result-label">{{ work.kind === 'image' ? '图片' : work.kind === 'video' ? '视频' : '文案' }} {{ index + 1 }}</h4>
      <pre v-if="work.kind === 'copy'" class="copy-result" :tabindex="compact ? 0 : undefined" :role="compact ? 'region' : undefined" :aria-label="compact ? '完整文案 ' + (index + 1) : undefined"><template v-if="documentLayout && item.text && item.text.indexOf('\n') > 0"><span class="copy-headline">{{ item.text.slice(0, item.text.indexOf('\n')) }}</span>{{ item.text.slice(item.text.indexOf('\n')) }}</template><template v-else>{{ item.text }}</template></pre>
      <img v-else-if="work.kind === 'image'" :src="fileContentUrl(item.file_id)" :alt="'完整生成作品 ' + (index + 1)" loading="eager" role="button" tabindex="0" aria-haspopup="dialog" :aria-label="'放大图片 ' + (index + 1)" @click="openPreview(index)" @keydown.enter.prevent="openPreview(index)" @keydown.space.prevent="openPreview(index)" />
      <video v-else :src="fileContentUrl(item.file_id)" controls preload="metadata" playsinline />
      <div class="action-row result-actions">
        <UiButton v-if="!(hideCopyFileActions && work.kind === 'copy')" class="button" type="button" @click="openPreview(index)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>预览</UiButton>
        <UiButton v-if="work.kind === 'copy' && item.text !== null" class="button copy-action" type="button" @click="copy(item.text)">复制文案</UiButton>
        <a v-if="!(hideCopyFileActions && work.kind === 'copy')" class="button" :href="fileContentUrl(item.file_id)" :download="work.work_id + (work.kind === 'copy' ? '.txt' : work.kind === 'image' ? '.png' : '.mp4')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5"/></svg>{{ work.items.length > 1 ? '下载 ' + (index + 1) : '下载' }}</a>
        <slot v-if="index === work.items.length - 1" name="actions" />
      </div>
    </div>
    <p v-if="!work.items.length" class="field-hint">暂无可展示的完整成果，请重新读取作品。</p>
    </template>
    <p v-if="galleryLayout || feedback" class="result-feedback" role="status">{{ feedback }}</p>
    <AppDialog v-model:open="preview" title="作品预览"><div v-if="preview && selectedItem" class="preview-gallery" @keydown.left.prevent="movePreview(-1)" @keydown.right.prevent="movePreview(1)">
      <nav v-if="work.kind !== 'copy' && work.items.length > 1" class="preview-navigation" aria-label="切换作品"><UiButton class="button" type="button" data-preview-previous :disabled="previewIndex === 0" @click="movePreview(-1)">{{ work.kind === 'image' ? '上一张' : '上一个' }}</UiButton><span role="status" aria-live="polite">{{ previewIndex + 1 }} / {{ work.items.length }}</span><UiButton class="button" type="button" data-preview-next :disabled="previewIndex === work.items.length - 1" @click="movePreview(1)">{{ work.kind === 'image' ? '下一张' : '下一个' }}</UiButton></nav>
      <template v-if="work.kind === 'copy'"><pre v-for="item in work.items" :key="item.file_id" class="copy-result preview-copy">{{ item.text }}</pre></template><img v-else-if="work.kind === 'image'" :key="selectedItem.file_id" class="preview-media preview-image" :src="fileContentUrl(selectedItem.file_id)" :alt="'完整生成作品预览 ' + (previewIndex + 1)" /><video v-else :key="selectedItem.file_id" class="preview-media" :src="fileContentUrl(selectedItem.file_id)" controls preload="metadata" playsinline />
    </div></AppDialog>
  </div>
</template>
<style scoped>
.result-item { margin:12px 0 0 }
.result-label { margin:0 0 12px; font-size:13px; font-weight:600; color:var(--color-muted) }
.result-item>img,.result-item>video { max-height:640px; border-radius:10px; object-fit:contain; height:auto }
.result-item>img { cursor:zoom-in }
.result-item>img:focus-visible { outline:2px solid var(--color-primary); outline-offset:3px }
.preview-image { width:100%; height:auto; max-height:none; object-fit:contain }
.preview-navigation { position:sticky; top:0; z-index:1; display:flex; align-items:center; justify-content:space-between; gap:12px; padding:0 0 12px; background:var(--color-surface,#fffdfa) }
.preview-navigation span { color:var(--color-muted); font-size:13px; font-variant-numeric:tabular-nums }
.result-actions { padding-top:14px; border-top:1px solid var(--color-border); margin-top:14px; gap:8px }
.result-actions .button { font-size:13px; padding:8px 12px }
.result-download-menu { align-self:center }
.result-download-menu svg { width:14px; height:14px; margin-left:4px }
.result-download-options :deep(.el-dropdown-menu__item) { min-height:44px; padding:8px 16px; font-size:13px }
.copy-result { font-size:14px; line-height:1.9; padding:20px }
.compact .result-item>.copy-result { display:block; max-height:280px; overflow-y:auto; overflow-x:hidden; white-space:pre-wrap; overflow-wrap:anywhere; overscroll-behavior:contain; scrollbar-gutter:stable; scrollbar-width:thin; scrollbar-color:transparent transparent }
.compact .result-item>.copy-result:hover,.compact .result-item>.copy-result:focus { scrollbar-color:var(--color-border) transparent }
.compact .result-item>.copy-result::-webkit-scrollbar { width:6px }
.compact .result-item>.copy-result::-webkit-scrollbar-thumb { border-radius:3px; background:transparent }
.compact .result-item>.copy-result:hover::-webkit-scrollbar-thumb,.compact .result-item>.copy-result:focus::-webkit-scrollbar-thumb { background:var(--color-border) }
.compact .result-item>.copy-result:focus-visible { outline:2px solid var(--color-primary); outline-offset:2px }
.compact .preview-copy { max-height:none; overflow:visible }
.compact .result-item>img,.compact .result-item>video { max-height:240px }
.gallery-layout .result-body { height:var(--work-body-height,280px); flex-shrink:0; overflow:auto; overscroll-behavior:contain; scrollbar-gutter:stable; scrollbar-width:thin; scrollbar-color:var(--color-border) transparent; border-radius:8px; background:var(--color-background) }
.gallery-layout .result-body:focus-visible { outline:2px solid var(--color-primary); outline-offset:2px }
.gallery-layout .result-body .result-item { margin:0; min-width:0 }
.gallery-layout .result-body .result-item + .result-item { margin-top:16px; padding-top:16px; border-top:1px solid var(--color-border) }
.gallery-layout .result-body .result-label { margin:12px 16px }
.gallery-layout .result-body .copy-result { height:auto; min-height:0; max-height:none; margin:0; padding:24px; overflow:visible; white-space:pre-wrap; overflow-wrap:anywhere; color:var(--color-text); font-size:15px; line-height:1.9 }
.gallery-layout .result-body .result-item>img,.gallery-layout .result-body .result-item>video { display:block; width:100%; height:auto; max-height:none; margin:0; object-fit:contain; border-radius:8px }
.gallery-layout .result-body .result-item>video { max-height:var(--work-body-height,280px) }
.gallery-layout .result-feedback { min-height:20px; margin:0 8px; font-size:12px; line-height:20px }
</style>
