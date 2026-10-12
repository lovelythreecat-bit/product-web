<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from './AppIcon.vue'
import AppDialog from './AppDialog.vue'
import ConversationList from '../features/workspace/ConversationList.vue'
import { session } from '../features/auth/session'
const about = ref(false), logoutError = ref('')
const router = useRouter()
watch(session.epoch, () => { logoutError.value = ''; about.value = false; if (session.profile.value) void session.refreshAccount().catch(() => {}) }, { immediate: true })
async function logout() { logoutError.value = ''; try { if (await session.logout()) await router.replace('/login') } catch { logoutError.value = '退出未完成，请重试。' } }
</script>
<template>
  <a class="skip-link" href="#main-content">跳到主要内容</a>
  <header class="app-header"><RouterLink class="brand" to="/workspace"><span class="brand-mark">C</span><span>商品创作台<small>暂定名称</small></span></RouterLink><nav v-if="session.profile.value" aria-label="主要导航"><RouterLink to="/workspace">创作工作台</RouterLink><RouterLink to="/works">我的作品</RouterLink><RouterLink to="/account">个人中心</RouterLink></nav><div v-if="session.profile.value" class="header-actions"><RouterLink class="button" data-testid="header-recharge" to="/recharge">充值积分</RouterLink><button type="button" class="button" :disabled="session.busy.value" @click="logout">退出登录</button></div><button type="button" class="icon-button" aria-label="开发说明" @click="about = true"><AppIcon name="info" /></button></header>
  <p v-if="logoutError" class="field-error" role="alert">{{ logoutError }}</p>
  <div class="shell-body" :class="{ 'public-shell': !session.profile.value }"><aside v-if="session.profile.value" class="shell-sidebar"><p class="environment">TEST_ONLY · 开发环境</p><ConversationList :key="session.epoch.value" /><div class="sidebar-bottom"><p>{{ session.account.value ? '可用积分 ' + session.account.value.available : '积分读取中' }}</p><small v-if="session.account.value">冻结 {{ session.account.value.frozen }} · 已消费 {{ session.account.value.consumed }}</small><small>在线充值暂未开放</small></div></aside><main id="main-content" tabindex="-1"><RouterView :key="session.epoch.value" /></main></div>
  <AppDialog v-model:open="about" title="开发说明"><p>当前使用 TEST_ONLY 模拟服务验证创作流程。</p><p>商品创作台为暂定名称，公开上线仍需完成品牌与业务政策确认。</p></AppDialog>
</template>
