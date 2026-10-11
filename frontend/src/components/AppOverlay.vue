<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount, useId } from 'vue'
import AppIcon from './AppIcon.vue'
const props = withDefaults(defineProps<{open:boolean; title:string; variant?:'dialog'|'drawer'; purpose?:'read'|'edit'|'charge'|'delete'}>(), {variant:'dialog',purpose:'read'})
const emit = defineEmits<{ 'update:open':[value:boolean] }>()
const element = ref<HTMLDialogElement>()
const heading = ref<HTMLElement>()
const cancel = ref<HTMLButtonElement>()
const titleId = useId()
let trigger: HTMLElement | null = null
let revision = 0
function close() { emit('update:open',false) }
watch(() => props.open, async open => {
  const current = ++revision
  if (open) trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
  await nextTick()
  if (current !== revision || !element.value) return
  if (open) {
    if (!element.value.open) element.value.showModal()
    await nextTick()
    if (current !== revision) return
    if (props.purpose === 'charge' || props.purpose === 'delete') cancel.value?.focus()
    else if (props.purpose === 'edit') { const initial = element.value.querySelector('[data-initial-focus]') as HTMLElement | null; (initial ?? heading.value)?.focus() }
    else heading.value?.focus()
  } else {
    if (element.value.open) element.value.close()
    trigger?.isConnected && trigger.focus()
  }
}, {immediate:true})
function trapTab(event: KeyboardEvent) {
  if (event.key !== 'Tab' || !element.value) return
  const controls = Array.from(element.value.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex]:not([tabindex="-1"])')).filter(el => el.getClientRects().length > 0 && !el.closest('[inert]'))
  const first = controls[0], last = controls.at(-1)
  if (!first) { event.preventDefault(); heading.value?.focus(); return }
  if (event.shiftKey && (document.activeElement === first || !controls.includes(document.activeElement as HTMLElement))) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}
function closed() { if (!element.value?.open && props.open) close() }
onBeforeUnmount(() => { revision++; if (element.value?.open) element.value.close(); if (props.open && trigger?.isConnected) trigger.focus() })
</script>
<template>
  <dialog ref="element" :class="['app-overlay', variant]" :aria-labelledby="titleId" @keydown="trapTab" @cancel.prevent="close" @close="closed">
    <header class="overlay-header"><h2 :id="titleId" ref="heading" tabindex="-1">{{ title }}</h2><button type="button" class="icon-button" aria-label="关闭" @click="close"><AppIcon name="close" /></button></header>
    <div class="overlay-content"><slot /></div>
    <footer class="overlay-actions">
      <button type="button" v-if="purpose !== 'read'" ref="cancel" class="button" @click="close">取消</button>
      <button type="button" v-else class="button" @click="close">关闭</button>
      <slot name="actions" />
    </footer>
  </dialog>
</template>
