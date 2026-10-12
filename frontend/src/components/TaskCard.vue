<script setup lang="ts">
import { onScopeDispose, ref, watch } from 'vue'
import type { Schema } from '../types/api'
import { getWork } from '../api/works'
import AppDrawer from './AppDrawer.vue'
import ResultViewer from './ResultViewer.vue'
import { session } from '../features/auth/session'
const props = defineProps<{ detail: Schema<'TaskDetail'>; agent?: Schema<'AgentVersion'>; fragment?: string }>()
defineEmits<{ regenerate: [work: Schema<'WorkDetail'>] }>()
const expanded = ref(false), works = ref<Schema<'WorkDetail'>[]>([]), error = ref('')
const states: Record<string, string> = { SUBMITTED: '已受理', QUEUED: '排队中', SUBMITTING: '提交中', RUNNING: '生成中', INVESTIGATING: '待核查，尚未成功', SAVING: '正在保存完整结果', SAVE_RECOVERY: '保存恢复中，尚未成功', SUCCEEDED: '生成成功', FAILED: '确定失败', MANUALLY_CLOSED: '人工关闭' }
const settlement: Record<string, string> = { FROZEN: '已冻结，尚未扣除', CONSUMED: '已消费', RELEASED: '已释放' }
let revision = 0, alive = true
onScopeDispose(() => { alive = false; revision++ })
watch(() => props.detail.task.work_ids.join(','), async () => { const stamp = ++revision, epoch = session.epoch.value; try { const values = await Promise.all(props.detail.task.work_ids.map(getWork)); if (alive && stamp === revision && epoch === session.epoch.value) works.value = values } catch { if (alive && stamp === revision) error.value = '部分作品已不可用，请在作品页核对。' } }, { immediate: true })
</script>
<template><article class="task-card" :data-task-id="detail.task.task_id"><div class="section-heading"><h2>{{ agent?.name || '创作任务' }}</h2><span class="status-label">{{ states[detail.task.state] }}</span></div><p class="task-instruction">{{ detail.input.instruction || '按商品资料创作' }}</p><p>{{ detail.task.quote.credits }} 积分 · {{ settlement[detail.task.settlement_state] }}</p><p v-if="detail.task.investigation_reason">{{ detail.task.investigation_reason }}</p><div v-if="fragment && agent?.kind === 'copy'" class="transient"><small>临时文案片段，尚未形成完整作品</small><p>{{ fragment }}</p></div><div v-for="work in works" :key="work.work_id"><ResultViewer :work="work" /><button class="button" type="button" @click="$emit('regenerate', work)">重新生成</button></div><p v-if="error" role="alert">{{ error }}</p><button class="button" type="button" @click="expanded = true">任务详情</button><AppDrawer v-model:open="expanded" title="任务详情"><dl class="detail-list"><dt>任务编号</dt><dd>{{ detail.task.task_id }}</dd><dt>会话编号</dt><dd>{{ detail.conversation_id }}</dd><dt>原 Agent</dt><dd>{{ detail.agent_id }} · {{ detail.task.quote.agent_version }}</dd><dt>执行与结算</dt><dd>{{ states[detail.task.state] }} / {{ settlement[detail.task.settlement_state] }}</dd><dt>原输入快照</dt><dd><pre>{{ JSON.stringify(detail.input, null, 2) }}</pre></dd><dt>原报价</dt><dd><pre>{{ JSON.stringify(detail.task.quote, null, 2) }}</pre></dd><dt>适用政策版本</dt><dd><pre>{{ JSON.stringify(detail.policy_versions, null, 2) }}</pre></dd></dl></AppDrawer></article></template>
