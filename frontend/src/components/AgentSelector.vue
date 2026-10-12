<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Schema } from '../types/api'
const props = defineProps<{ agents: Schema<'AgentVersion'>[]; modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [id: string] }>()
const kind = ref('')
watch(() => props.modelValue, id => {
  const selected = props.agents.find(agent => agent.agent_id === id)
  if (selected) kind.value = selected.kind
}, { immediate: true })
const visible = computed(() => props.agents.filter(a => a.enabled && (!kind.value || a.kind === kind.value)))
function chooseKind(value: string) { kind.value = value; if (!visible.value.some(a => a.agent_id === props.modelValue)) emit('update:modelValue', '') }
</script>
<template>
  <div class="agent-types" aria-label="创作类型"><button v-for="item in [{kind:'copy',label:'文案'},{kind:'image',label:'图片'},{kind:'video',label:'视频'}]" :key="item.kind" type="button" class="button" :aria-pressed="kind === item.kind" @click="chooseKind(item.kind)">{{ item.label }}</button></div>
  <label for="agent-choice">选择 Agent</label><select id="agent-choice" :value="modelValue" @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"><option value="">请手动选择</option><option v-for="agent in visible" :key="agent.agent_id" :value="agent.agent_id">{{ agent.name }} · {{ agent.agent_id.slice(0, 8) }}</option></select>
</template>
