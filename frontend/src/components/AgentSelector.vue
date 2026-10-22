<script setup lang="ts">
import UiButton from './ui/UiButton.vue'
import { computed, ref, watch } from 'vue'
import type { Schema } from '../types/api'
const props = defineProps<{ agents: Schema<'AgentVersion'>[]; modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [id: string] }>()
const kind = ref('')
watch(() => [props.modelValue, props.agents] as const, ([id]) => {
  const selected = props.agents.find(agent => agent.agent_id === id)
  if (selected) kind.value = selected.kind
}, { immediate: true })
const visible = computed(() => props.agents.filter(a => a.enabled && a.kind === kind.value))
function chooseKind(value: string) { kind.value = value; if (!visible.value.some(a => a.agent_id === props.modelValue)) emit('update:modelValue', visible.value.length === 1 ? visible.value[0].agent_id : '') }
</script>
<template>
  <div class="agent-picker"><div class="agent-types" role="group" aria-label="创作类型"><UiButton v-for="item in [{kind:'copy',label:'文案'},{kind:'image',label:'图片'},{kind:'video',label:'视频'}]" :key="item.kind" type="button" class="button" :aria-pressed="kind === item.kind" @click="chooseKind(item.kind)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path v-if="item.kind === 'copy'" d="M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6 M9 16h6"/><path v-else-if="item.kind === 'image'" d="M4 4h16v16H4z M4 16l5-5 4 4 3-3 4 4 M8 8h.01"/><path v-else d="M4 5h16v14H4z M10 9l5 3-5 3z"/></svg>{{ item.label }}</UiButton></div>
  <p v-if="!kind" class="field-hint">请选择文案、图片或视频，开始本次创作。</p>
  <p v-else-if="visible.length > 1" class="field-hint">当前创作类型的服务配置需要确认，请联系管理员。</p>
  <p v-if="kind && !visible.length" class="field-hint">当前暂无可用的{{ kind === 'copy' ? '文案' : kind === 'image' ? '图片' : '视频' }} Agent。</p></div>
</template>
<style scoped>
.agent-picker { display:grid; gap:10px }
.agent-types { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:4px; padding:4px; border-radius:10px; background:var(--color-background) }
.agent-types .button { padding:9px 6px; gap:8px; font-size:14px; min-height:44px; border-color:transparent; background:transparent; color:var(--color-muted) }
.agent-types .button[aria-pressed=true] { background:var(--color-panel); border-color:var(--color-border); color:var(--color-primary); font-weight:600; box-shadow:0 1px 3px color-mix(in srgb,var(--color-text) 6%,transparent) }
.field-hint { font-size:13px; line-height:1.6 }
@media(hover:hover) { .agent-types .button:hover { background:var(--color-selected); color:var(--color-primary); filter:none } }
</style>
