<script setup lang="ts">
import AppShell from './components/AppShell.vue'
import { ElConfigProvider } from 'element-plus/es/components/config-provider/index'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { onMounted, onUnmounted, watch } from 'vue'
import { refreshBrand } from './features/site/brand'
import { session } from './features/auth/session'
const refresh = () => { void refreshBrand().catch(() => {}) }
watch(session.epoch, refresh)
onMounted(() => { refresh(); window.addEventListener('focus', refresh) })
onUnmounted(() => window.removeEventListener('focus', refresh))
</script>
<template><ElConfigProvider :locale="zhCn"><AppShell /></ElConfigProvider></template>
