<script setup lang="ts">
import { computed, onMounted, ref, useAttrs } from 'vue'
import { ElAutocomplete, type AutocompleteInstance } from 'element-plus/es/components/autocomplete/index'
import { ElInput } from 'element-plus/es/components/input/index'

defineOptions({ inheritAttrs: false })
const props = withDefaults(defineProps<{
  modelValue?: string | number | null
  value?: string | number | boolean | null
  type?: string
  modelModifiers?: { number?: boolean; trim?: boolean; lazy?: boolean }
  suggestions?: readonly string[]
}>(), { type: 'text', value: undefined })
const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  input: [event: Event]
  change: [event: Event]
}>()
const attrs = useAttrs()
const root = ref<HTMLElement>()
const autocomplete = ref<AutocompleteInstance>()
let browsingSuggestions = true
const current = computed(() => {
  const value = props.modelValue ?? props.value ?? ''
  return typeof value === 'boolean' ? String(value) : value
})
function nativeInput() { return root.value?.querySelector('input,textarea') as HTMLInputElement | HTMLTextAreaElement | null }
onMounted(() => { if (attrs.id && nativeInput()) nativeInput()!.id = String(attrs.id) })
function domEvent(type: string, value: string | number) {
  const input = nativeInput()
  if (input) input.value = String(value)
  const event = new Event(type, { bubbles: true })
  Object.defineProperty(event, 'target', { value: input })
  return event
}
function normalize(value: string | number) {
  const text = props.modelModifiers?.trim ? String(value).trim() : String(value)
  if (props.modelModifiers?.number || props.type === 'number') {
    const number = Number.parseFloat(text)
    return Number.isNaN(number) ? text : number
  }
  return text
}
function update(value: string | number) {
  if (nativeInput()?.matches(':disabled')) return
  browsingSuggestions = false
  if (!props.modelModifiers?.lazy) emit('update:modelValue', normalize(value))
  emit('input', domEvent('input', value))
}
function change(value: string | number) {
  if (nativeInput()?.matches(':disabled')) return
  if (props.modelModifiers?.lazy) emit('update:modelValue', normalize(value))
  emit('change', domEvent('change', value))
}
function suggest(query: string, done: (items: { value: string }[]) => void) {
  const search = browsingSuggestions ? '' : query.toLowerCase()
  done((props.suggestions ?? []).filter(value => value.toLowerCase().includes(search)).map(value => ({ value })))
}
function browseSuggestions() {
  if (nativeInput()?.matches(':disabled,[readonly]')) return
  browsingSuggestions = true
  if (!autocomplete.value) return
  autocomplete.value.activated = true
  void autocomplete.value.getData('')
}
function focus() { nativeInput()?.focus() }
defineExpose({ focus })
</script>

<template>
  <div ref="root" class="ui-input-field">
    <ElAutocomplete v-if="suggestions" ref="autocomplete" v-bind="attrs" class="ui-input ui-autocomplete" :model-value="String(current)" :fetch-suggestions="suggest" :debounce="0" :teleported="true" @focus="browseSuggestions" @click="browseSuggestions" @update:model-value="update" @change="change" />
    <ElInput v-else v-bind="attrs" class="ui-input" :type="type" :rows="attrs.rows ? Number(attrs.rows) : undefined" :model-value="current" @update:model-value="update" @change="change" />
  </div>
</template>
