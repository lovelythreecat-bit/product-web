<script setup lang="ts">
import { theme, setTheme } from '../styles/theme'
</script>
<template>
  <button type="button" class="theme-toggle icon-button" :aria-label="theme === 'light' ? '切换深色主题' : '切换浅色主题'" :title="theme === 'light' ? '切换深色主题' : '切换浅色主题'" @click="setTheme(theme === 'light' ? 'dark' : 'light')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path v-if="theme === 'light'" d="M20.5 14.1A8.5 8.5 0 0 1 9.9 3.5 8.5 8.5 0 1 0 20.5 14.1Z" />
      <template v-else><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></template>
    </svg>
  </button>
</template>
<style scoped>
.theme-toggle { flex-shrink:0; color:var(--color-muted); background:var(--color-panel); }
.theme-toggle:hover { color:var(--color-primary); background:var(--color-background); }
</style>
