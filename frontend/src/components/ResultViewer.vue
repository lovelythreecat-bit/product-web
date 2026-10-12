<script setup lang="ts">
import { ref } from 'vue'
import type { Schema } from '../types/api'
import { fileContentUrl } from '../api/files'
import AppDialog from './AppDialog.vue'
defineProps<{ work: Schema<'WorkView'> }>()
const preview = ref(false), feedback = ref('')
async function copy(text: string) { try { await navigator.clipboard.writeText(text); feedback.value = '已复制完整文案' } catch { feedback.value = '无法自动复制，请选择文案复制。' } }
</script>
<template><div class="result-viewer"><div v-for="item in work.items" :key="item.file_id" class="result-item"><pre v-if="work.kind === 'copy'" class="copy-result">{{ item.text }}</pre><img v-else-if="work.kind === 'image'" :src="fileContentUrl(item.file_id)" alt="完整生成作品" loading="lazy" /><video v-else :src="fileContentUrl(item.file_id)" controls preload="metadata" playsinline /><div class="action-row"><button v-if="work.kind === 'copy' && item.text !== null" class="button" type="button" @click="copy(item.text)">复制文案</button><a class="button" :href="fileContentUrl(item.file_id)" :download="work.work_id + (work.kind === 'copy' ? '.txt' : work.kind === 'image' ? '.png' : '.mp4')">下载</a></div></div><button class="button" type="button" @click="preview = true">预览</button><p v-if="feedback" role="status">{{ feedback }}</p><AppDialog v-model:open="preview" title="作品预览"><template v-for="item in work.items" :key="item.file_id"><pre v-if="work.kind === 'copy'" class="copy-result">{{ item.text }}</pre><img v-else-if="work.kind === 'image'" class="preview-media" :src="fileContentUrl(item.file_id)" alt="完整生成作品预览" /><video v-else class="preview-media" :src="fileContentUrl(item.file_id)" controls preload="metadata" playsinline /></template></AppDialog></div></template>
