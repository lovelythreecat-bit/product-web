<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Schema } from '../types/api'
import { getFileContentBlob } from '../api/files'
import { session } from '../features/auth/session'
const props = withDefaults(defineProps<{ avatar?: Schema<'FileVersionRef'> | null; name: string; size?: number }>(), { size: 36 })
const source = ref('')
const initial = computed(() => Array.from(props.name.trim())[0] || '用')
const dimension = computed(() => `${Math.max(24, Math.min(props.size, 160))}px`)
function release() { if (source.value) URL.revokeObjectURL(source.value); source.value = '' }
watch(() => [props.avatar?.file_id, props.avatar?.version, session.epoch.value, session.profile.value?.user_id] as const, async ([fileId, version, epoch, userId], _previous, onCleanup) => {
  release()
  const controller = new AbortController()
  onCleanup(() => { controller.abort(); release() })
  if (!fileId || !version || !userId) return
  try {
    const blob = await getFileContentBlob(fileId, controller.signal)
    if (controller.signal.aborted || epoch !== session.epoch.value || userId !== session.profile.value?.user_id || fileId !== props.avatar?.file_id || version !== props.avatar?.version) return
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(blob.type)) return
    source.value = URL.createObjectURL(blob)
  } catch { /* Avatar failure keeps a usable account trigger. */ }
}, { immediate: true, flush: 'sync' })
</script>
<template>
  <span class="user-avatar" :style="{ width: dimension, height: dimension }" aria-hidden="true">
    <img v-if="source" :src="source" alt="" @error="release" />
    <span v-else>{{ initial }}</span>
  </span>
</template>
<style scoped>
.user-avatar { display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; overflow:hidden; border:1px solid var(--color-border,#e7d9ca); border-radius:50%; background:var(--color-selected,#f2dfcf); color:var(--color-primary,#a94e32); font-size:clamp(14px,1.1em,24px); font-weight:600; line-height:1; }
.user-avatar img { width:100%; height:100%; object-fit:cover; }
</style>
