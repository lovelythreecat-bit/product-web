<script setup lang="ts">
import AppShell from './components/AppShell.vue'
import { ElConfigProvider } from 'element-plus/es/components/config-provider/index'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
</script>
<template><ElConfigProvider :locale="zhCn"><AppShell /></ElConfigProvider></template>
