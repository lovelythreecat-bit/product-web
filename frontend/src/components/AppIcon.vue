<script setup lang="ts">
defineProps<{ name: 'create'|'works'|'account'|'credits'|'close'|'info'|'menu' }>()
const paths = {create:'M12 5v14M5 12h14',works:'M4 4h16v16H4z M4 16l5-5 4 4 3-3 4 4 M8 8h.01',account:'M8 7a4 4 0 1 0 8 0 4 4 0 1 0-8 0 M4 21a8 8 0 0 1 16 0',credits:'M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0 M12 7v10 M15 9H10a2 2 0 0 0 0 4h4a2 2 0 0 1 0 4H9',close:'M6 6l12 12M6 18L18 6',info:'M12 10v7M12 7h.01 M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',menu:'M4 6h16M4 12h16M4 18h16'}
</script>
<template><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name]" /></svg></template>
