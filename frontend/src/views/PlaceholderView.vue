<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
const route = useRoute()
</script>
<template><section class="panel placeholder"><AppIcon name="info" /><h2>业务页面正在开发</h2><p>本次仅接入共享界面与接口基础。这里还没有可操作的{{ route.meta.title }}流程。</p><p>任务、作品和积分将以登录后的服务端记录为准。</p></section></template>
