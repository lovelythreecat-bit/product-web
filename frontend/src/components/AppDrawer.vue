<script setup lang="ts">
import AppOverlay from './AppOverlay.vue'
withDefaults(defineProps<{open:boolean; title:string; purpose?:'read'|'edit'|'charge'|'delete'; showFooter?:boolean}>(), { showFooter: true })
defineEmits<{ 'update:open':[value:boolean] }>()
</script>
<template><AppOverlay v-bind="$props" variant="drawer" @update:open="$emit('update:open',$event)"><slot /><template #actions><slot name="actions" /></template></AppOverlay></template>
