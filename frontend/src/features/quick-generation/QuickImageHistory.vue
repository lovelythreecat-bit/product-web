<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { QuickView } from '../../api/quickGeneration'
import type { Schema } from '../../types/api'
import AppDrawer from '../../components/AppDrawer.vue'
import TaskCard from '../../components/TaskCard.vue'
import UiButton from '../../components/ui/UiButton.vue'

const props = defineProps<{ run: QuickView; item: Schema<'QuickBatchItem'>; agents: Schema<'AgentVersion'>[] }>()
const open = ref(false)
const title = computed(() => `${props.item.label}历史版本`)
watch([() => props.run.run_id, () => props.item.task_id], () => { open.value = false })
const versions = computed(() => {
  const batches = props.run.state.batches || []
  const currentIndex = batches.findIndex(batch => batch.id === props.run.state.current.image)
  const currentId = props.item.task_id ? props.run.tasks[props.item.task_id]?.task.task_id : undefined
  const output = props.item.request.input.parameters.output_type
  const seen = new Set<string>()
  const result: { detail: Schema<'TaskDetail'>; version: number }[] = []
  for (const batch of batches.slice(0, currentIndex + 1)) {
    if (batch.kind !== 'image' || !batch.submitted) continue
    for (const item of batch.items) {
      if (item.request.input.parameters.output_type !== output) continue
      const detail = item.task_id ? props.run.tasks[item.task_id] : undefined
      if (!detail || detail.task.state !== 'SUCCEEDED' || item.task_id === props.item.task_id || detail.task.task_id === currentId || seen.has(detail.task.task_id)) continue
      seen.add(detail.task.task_id)
      result.push({ detail, version: result.length + 1 })
    }
  }
  return result.reverse()
})
</script>

<template>
  <div class="quick-image-history">
    <UiButton type="button" class="button text-button" :aria-label="title" :aria-expanded="open" @click="open = true">历史版本（{{ versions.length }}）</UiButton>
    <AppDrawer v-model:open="open" :title="title" purpose="read">
      <div v-if="open" class="quick-image-versions">
        <p v-if="!versions.length" class="field-hint">暂无历史版本，重新生成后可在这里查看之前的图片。</p>
        <p v-else class="field-hint">这里只展示{{ item.label }}重新生成之前的版本，可预览和下载。<template v-if="item.request.input.parameters.output_type === 'detail_page'">详情图每版包含完整的 3 张图片。</template></p>
        <section v-for="entry in versions" :key="entry.detail.task.task_id" class="quick-image-version">
          <h3>{{ item.label }} · 第 {{ entry.version }} 版</h3>
          <TaskCard :detail="entry.detail" :agent="agents.find(agent => agent.agent_id === entry.detail.agent_id)" quick-generation read-only />
        </section>
      </div>
    </AppDrawer>
  </div>
</template>

<style scoped>
.quick-image-versions { min-width:0 }
.quick-image-version + .quick-image-version { margin-top:24px; padding-top:20px; border-top:1px solid var(--color-border) }
.quick-image-version h3 { display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin:0 0 12px; font-size:15px }
</style>
