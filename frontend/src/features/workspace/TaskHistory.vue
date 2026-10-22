<script setup lang="ts">
import { computed, onScopeDispose, ref, watch } from 'vue'
import type { Schema } from '../../types/api'
import { getTaskHistory } from '../../api/tasks'
import { session } from '../auth/session'
import AppDrawer from '../../components/AppDrawer.vue'
import TaskCard from '../../components/TaskCard.vue'
import UiButton from '../../components/ui/UiButton.vue'

const props = defineProps<{ detail: Schema<'TaskDetail'>; agents: Schema<'AgentVersion'>[] }>()
const open = ref(false), loading = ref(false), error = ref('')
const versions = ref<Schema<'TaskDetail'>[]>([])
const title = computed(() => {
  const kind = props.agents.find(agent => agent.agent_id === props.detail.agent_id)?.kind
  return kind === 'image' ? '图片历史版本' : kind === 'copy' ? '文案历史版本' : '历史版本'
})
let revision = 0, alive = true
const epoch = session.epoch.value
onScopeDispose(() => { alive = false; revision++ })
watch(() => props.detail.task.task_id, () => { revision++; open.value = false; versions.value = []; error.value = ''; loading.value = false })
async function load() {
  const stamp = ++revision, taskId = props.detail.task.task_id
  const current = () => alive && epoch === session.epoch.value && revision === stamp && taskId === props.detail.task.task_id
  loading.value = true; error.value = ''
  try {
    const values = await getTaskHistory(taskId)
    if (current()) versions.value = values
  } catch { if (current()) error.value = '历史版本暂时无法读取，请重试。' }
  finally { if (current()) loading.value = false }
}
function show() { open.value = true; void load() }
</script>

<template>
  <div class="task-version-history">
    <UiButton type="button" class="button text-button" :aria-label="title" :aria-expanded="open" @click="show">历史版本</UiButton>
    <AppDrawer v-model:open="open" :title="title" purpose="read">
      <template v-if="open">
        <p v-if="loading" role="status">正在读取历史版本…</p>
        <div v-else-if="error"><p class="field-error" role="alert">{{ error }}</p><UiButton class="button" type="button" @click="load">重新读取历史版本</UiButton></div>
        <p v-else-if="!versions.length" class="field-hint">暂无历史版本，重新生成后可在这里查看之前的成果。</p>
        <template v-else>
          <p class="field-hint">这里只展示本任务重新生成之前的成果，可预览、复制或下载。</p>
          <section v-for="entry in versions" :key="entry.task.task_id" class="task-history-version">
            <TaskCard :detail="entry" :agent="agents.find(agent => agent.agent_id === entry.agent_id)" read-only />
          </section>
        </template>
      </template>
    </AppDrawer>
  </div>
</template>

<style scoped>
.task-version-history { min-width:0 }
.task-history-version + .task-history-version { margin-top:24px; padding-top:20px; border-top:1px solid var(--color-border) }
</style>
