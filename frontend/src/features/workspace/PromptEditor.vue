<script setup lang="ts">
import { ref, watch, onScopeDispose } from 'vue'
import { preparePrompt } from '../../api/assist'
import { createIntent, type Intent, ApiError } from '../../api/client'
import type { Schema } from '../../types/api'
import { session } from '../auth/session'
const props = defineProps<{ modelValue: string; request: Schema<'AssistRequest'> | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const suggestion = ref<string | null>(null), original = ref<string | undefined>(), busy = ref(false), error = ref('')
let intent: Intent<Schema<'AssistRequest'>> | undefined, revision = 0, alive = true
onScopeDispose(() => { alive = false; revision++ })
watch(() => JSON.stringify(props.request), () => { revision++; suggestion.value = null; intent = undefined; error.value = '' })
async function assist() {
  if (!props.request || busy.value) return
  busy.value = true; error.value = ''
  const stamp = revision, epoch = session.epoch.value
  intent ??= createIntent(props.request)
  try { const result = await preparePrompt(intent); if (!alive || stamp !== revision || epoch !== session.epoch.value) return; original.value = result.original; suggestion.value = result.proposed; intent = undefined }
  catch (e) { if (alive && stamp === revision) error.value = e instanceof ApiError ? e.message : '辅助暂时不可用。' }
  finally { if (alive) busy.value = false }
}
function adopt() { if (suggestion.value !== null) emit('update:modelValue', suggestion.value); suggestion.value = null }
function undo() { if (original.value !== undefined) emit('update:modelValue', original.value); original.value = undefined; suggestion.value = null; intent = undefined }
</script>
<template><div class="prompt-editor"><label for="creation-instruction">创作指令</label><textarea id="creation-instruction" rows="5" :value="modelValue" @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)" /><div class="action-row"><button class="button" type="button" :disabled="!request || busy" @click="assist">{{ busy ? '正在完善…' : intent ? '重试本次辅助' : 'AI 帮我完善' }}</button><button v-if="original !== undefined" class="button" type="button" @click="undo">撤回辅助</button></div><div v-if="suggestion !== null" class="assist-preview"><label for="assist-suggestion">AI 建议（可编辑）</label><textarea id="assist-suggestion" v-model="suggestion" rows="5" /><p>请核对商品事实后采用。辅助不会创建生成任务。</p><div class="action-row"><button class="button primary" type="button" @click="adopt">采用建议</button><button class="button" type="button" @click="suggestion = null">取消建议</button><button class="button" type="button" :disabled="busy" @click="assist">再次优化</button></div></div><p v-if="error" class="field-error" role="alert">{{ error }}</p></div></template>
