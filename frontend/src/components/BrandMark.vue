<script setup lang="ts">
import brandMark from '../assets/brand-mark.svg'
</script>
<template><img class="brand-symbol" :src="brandMark" alt="" aria-hidden="true" width="40" height="40" /></template>
<style scoped>
.brand-symbol { display:block; flex-shrink:0; object-fit:contain }
</style>
