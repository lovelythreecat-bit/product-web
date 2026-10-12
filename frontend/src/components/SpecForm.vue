<script setup lang="ts">
import type { Schema } from '../types/api'
defineProps<{ specs: Schema<'SpecVersion'>[]; specId: string; parameters: Record<string, string | number | boolean> }>()
const emit = defineEmits<{ spec: [id: string]; parameter: [name: string, value: string | number | boolean | undefined] }>()
const labels: Record<string, string> = { tone: '文案语气', purpose: '图片用途', aspect_ratio: '视频比例', subtitles: '字幕' }
function value(event: Event, kind: string) { const text = (event.target as HTMLInputElement).value; return text === '' ? undefined : kind === 'integer' ? Number(text) : kind === 'boolean' ? text === 'true' : text }
</script>
<template>
  <label for="spec-choice">生成规格</label><select id="spec-choice" :value="specId" @change="emit('spec', ($event.target as HTMLSelectElement).value)"><option value="">请选择当前规格</option><option v-for="spec in specs" :key="spec.spec_id" :value="spec.spec_id">{{ spec.name }}</option></select>
  <template v-for="(rule, name) in specs.find(s => s.spec_id === specId)?.parameter_schema.fields" :key="name">
    <label :for="'parameter-' + name">{{ labels[name] || name }}{{ rule.required ? '（必填）' : '' }}</label>
    <select v-if="rule.choices || rule.kind === 'boolean'" :id="'parameter-' + name" :value="parameters[name] === undefined ? '' : String(parameters[name])" @change="emit('parameter', name, value($event, rule.kind))"><option value="">请选择</option><option v-for="choice in (rule.choices || [true, false])" :key="String(choice)" :value="String(choice)">{{ typeof choice === 'boolean' ? choice ? '开启' : '关闭' : choice }}</option></select>
    <input v-else :id="'parameter-' + name" :type="rule.kind === 'integer' ? 'number' : 'text'" :value="parameters[name]" :min="rule.minimum ?? undefined" :max="rule.maximum ?? undefined" :maxlength="rule.max_length ?? undefined" @input="emit('parameter', name, value($event, rule.kind))" />
  </template>
</template>
