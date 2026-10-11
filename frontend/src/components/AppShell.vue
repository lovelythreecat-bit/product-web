<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from './AppIcon.vue'
import AppDialog from './AppDialog.vue'
const about = ref(false)
</script>
<template><a class="skip-link" href="#main-content">跳到主要内容</a><header class="app-header"><RouterLink class="brand" to="/workspace"><span class="brand-mark">C</span><span>商品创作台<small>暂定名称</small></span></RouterLink><nav aria-label="主要导航"><RouterLink to="/workspace">创作工作台</RouterLink><RouterLink to="/works">我的作品</RouterLink><RouterLink to="/account">个人中心</RouterLink></nav><button class="icon-button" aria-label="开发说明" @click="about = true"><AppIcon name="info" /></button></header><div class="shell-body"><aside class="shell-sidebar"><p class="environment">TEST_ONLY · 开发环境</p><div class="sidebar-top"><AppIcon name="create" /><strong>创作空间</strong></div><p>历史会话将在业务页面接入后显示。</p><div class="sidebar-bottom"><p>积分信息待接入</p><RouterLink class="button" to="/recharge"><AppIcon name="credits" />充值积分</RouterLink><small>在线充值暂未开放</small></div></aside><main id="main-content" tabindex="-1"><RouterView /></main></div><AppDialog v-model:open="about" title="开发说明"><p>共享界面基础已接入，业务流程仍在开发。</p><p>商品创作台为暂定名称，公开上线仍需完成品牌与业务政策确认。</p></AppDialog></template>
