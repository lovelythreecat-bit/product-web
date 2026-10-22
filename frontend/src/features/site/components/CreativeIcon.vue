<script setup lang="ts">
defineProps<{ type: 'text' | 'image' | 'video' | 'arrow' }>()
</script>
<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <template v-if="type === 'text'"><path d="m15 3 6 6M4 14 16 2l6 6-12 12-8 2 2-8Z"/><path d="m4 14 6 6M2 22h19"/></template>
    <template v-else-if="type === 'image'"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1"/><path d="m3 17 5-5 4 4 4-6 5 7"/></template>
    <template v-else-if="type === 'video'"><circle cx="12" cy="12" r="10"/><path d="m10 7 7 5-7 5V7Z"/></template>
    <template v-else><path d="M4 12h16m-6-6 6 6-6 6"/></template>
  </svg>
</template>
