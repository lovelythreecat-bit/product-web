<script setup lang="ts">
import { onScopeDispose, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Schema } from '../../types/api'
import { createQuickRun, listQuickRuns } from '../../api/quickGeneration'
import UiButton from '../../components/ui/UiButton.vue'
const router = useRouter(), runs = ref<Schema<'QuickSummary'>[]>([])
const loading = ref(true), busy = ref(false), error = ref('')
const stages = ['商品确认', '营销文案', '图片生成', '视频生成', '已完成']
let alive = true, creationId = ''
onScopeDispose(() => { alive = false })
async function load() { loading.value = true; error.value = ''; try { const value = await listQuickRuns(); if (alive) runs.value = value } catch (cause) { if (alive) error.value = cause instanceof Error ? cause.message : '进度暂时无法读取。' } finally { if (alive) loading.value = false } }
async function create() {
  if (busy.value) return
  busy.value = true; error.value = ''; creationId ||= crypto.randomUUID()
  try { const value = await createQuickRun(creationId); if (alive) await router.push('/workspace/quick/' + value.run_id) }
  catch (cause) { if (alive) error.value = cause instanceof Error ? cause.message : '创建失败，请重试。' }
  finally { if (alive) busy.value = false }
}
void load()
</script>
<template>
  <div class="quick-entry">
    <div class="quick-entry-intro"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6Z"/></svg><h2>从一个商品，开始一整套创作</h2><p>准备一次商品资料，按步骤确认文案、图片与视频。</p><UiButton class="button primary" type="button" :disabled="busy" @click="create">{{ busy ? '正在创建…' : '开始快速生成' }}</UiButton><p class="field-hint">每个生成阶段单独确认费用，完整成果保存后消费积分。</p></div>
    <section class="quick-saved"><div class="section-heading"><h2>已保存的快速生成</h2><UiButton class="button" type="button" :disabled="loading" @click="load">刷新进度</UiButton></div><p v-if="loading" role="status">正在读取进度…</p><p v-else-if="!runs.length && !error">暂无保存的快速生成，开始准备一件商品吧。</p><p v-if="error" class="field-error" role="alert">{{ error }}</p><RouterLink v-for="run in runs" :key="run.run_id" class="quick-saved-row" :to="'/workspace/quick/' + run.run_id"><strong>{{ run.title }}</strong><span>{{ stages[run.step - 1] }}<span aria-hidden="true"> →</span></span></RouterLink></section>
  </div>
</template>
