<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'
import { ElDialog } from 'element-plus/es/components/dialog/index'
import { ElDrawer } from 'element-plus/es/components/drawer/index'
import UiButton from './ui/UiButton.vue'
import AppIcon from './AppIcon.vue'
const props = withDefaults(defineProps<{ open: boolean; title: string; variant?: 'dialog' | 'drawer'; purpose?: 'read' | 'edit' | 'charge' | 'delete'; showFooter?: boolean }>(), { variant: 'dialog', purpose: 'read', showFooter: true })
const emit = defineEmits<{ 'update:open': [value: boolean] }>()
const content = ref<HTMLElement>(), heading = ref<HTMLElement>()
const cancel = ref<InstanceType<typeof UiButton>>()
const titleId = useId()
let trigger: HTMLElement | null = null
watch(() => props.open, open => { if (open) trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null }, { flush: 'sync', immediate: true })
function close() { emit('update:open', false) }
async function opened(event?: Event) {
  event?.preventDefault()
  await nextTick()
  if (!props.open) return
  if (props.purpose === 'charge' || props.purpose === 'delete') cancel.value?.focus()
  else if (props.purpose === 'edit') {
    const initial = content.value?.querySelector<HTMLElement>('[data-initial-focus]')
    // Element Plus selects have a tabindex=-1 wrapper before their input.
    // Prefer the actual control so edit drawers start at an editable field.
    const field = initial?.matches('input,textarea,button') ? initial
      : initial?.querySelector<HTMLElement>('input,textarea,button')
        ?? (initial?.matches('[tabindex]') ? initial : initial?.querySelector<HTMLElement>('[tabindex]'))
    ;(field ?? heading.value)?.focus()
  } else heading.value?.focus()
}
function restore(event?: Event) { event?.preventDefault(); if (trigger?.isConnected) trigger.focus() }
onBeforeUnmount(() => { if (props.open) restore() })
</script>
<template>
  <component :is="variant === 'drawer' ? ElDrawer : ElDialog" :model-value="open" :class="['app-overlay', variant]" :title="title" :aria-labelledby="titleId" :show-close="false" :close-on-click-modal="false" :close-on-press-escape="false" :destroy-on-close="true" :append-to-body="true" :size="'min(480px, 100vw)'" :width="'min(560px, calc(100vw - 32px))'" @update:model-value="value => !value && close()" @open-auto-focus="opened" @opened="opened" @close-auto-focus="restore">
    <template #header><header class="overlay-header"><h2 :id="titleId" ref="heading" tabindex="-1">{{ title }}</h2><UiButton type="button" class="icon-button" aria-label="关闭" @click="close"><AppIcon name="close" /></UiButton></header></template>
    <div ref="content" class="overlay-content"><slot /></div>
    <template v-if="showFooter" #footer><footer class="overlay-actions"><UiButton v-if="purpose !== 'read'" ref="cancel" type="button" class="button" @click="close">取消</UiButton><UiButton v-else type="button" class="button" @click="close">关闭</UiButton><slot name="actions" /></footer></template>
  </component>
</template>
