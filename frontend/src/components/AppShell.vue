<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from './AppIcon.vue'
import BrandMark from './BrandMark.vue'
import UserMenu from './UserMenu.vue'
import ConversationList from '../features/workspace/ConversationList.vue'
import { session } from '../features/auth/session'
import '../styles/app-header.css'

const route = useRoute()
const isHome = computed(() => route.path === '/')
const isAuth = computed(() => ['/login', '/register'].includes(route.path))
const inWorkspace = computed(() => route.path.startsWith('/workspace'))
const inAdmin = computed(() => route.path.startsWith('/admin'))
const inCollection = computed(() => ['/works', '/account'].includes(route.path))
const adminListPage = computed(() => ['/admin/tasks', '/admin/users', '/admin/credits', '/admin/logs'].includes(route.path))
const showSidebar = computed(() => !!session.profile.value && (inWorkspace.value || inAdmin.value))
const adminLinks = [{to:'/admin/tasks',label:'任务与异常'},{to:'/admin/users',label:'用户管理'},{to:'/admin/credits',label:'积分管理'},{to:'/admin/agents',label:'Agent 配置'},{to:'/admin/parameters',label:'参数配置'},{to:'/admin/usage',label:'运营总览'},{to:'/admin/logs',label:'操作日志'}]
watch(session.epoch, () => { if (session.profile.value) void session.refreshAccount().catch(() => {}) }, { immediate: true })

</script>
<template>
  <div class="app-shell" :class="{ 'app-shell--auth': isAuth, 'app-shell--workspace': showSidebar && inWorkspace, 'app-shell--admin': showSidebar && inAdmin, 'app-shell--admin-list': showSidebar && adminListPage, 'app-shell--collection': inCollection }">
  <a class="skip-link" href="#main-content">跳到主要内容</a>
  <header v-if="!isHome" class="app-header" :class="{ 'app-header--authenticated': !!session.profile.value, 'app-header--studio': !!session.profile.value && (inWorkspace || inCollection || inAdmin) }">
    <RouterLink class="brand" to="/" target="_blank" rel="noopener noreferrer" aria-label="映作首页（新标签页打开）"><BrandMark class="brand-mark" /><span>映作</span></RouterLink>
    <nav v-if="session.profile.value" aria-label="主要导航">
      <RouterLink to="/workspace" :class="{ 'router-link-active': inWorkspace }" :aria-current="inWorkspace ? 'page' : undefined">创作工作台</RouterLink>
      <RouterLink to="/works">我的作品</RouterLink>
      <RouterLink to="/account">个人中心</RouterLink>
      <RouterLink v-if="session.profile.value.role === 'admin'" to="/admin" :class="{ 'router-link-active': inAdmin }" :aria-current="inAdmin ? 'page' : undefined">管理后台</RouterLink>
    </nav>
    <div v-if="session.profile.value" class="header-actions">
      <UserMenu class="shell-user-menu" />
    </div>
    <div v-else class="header-actions"><RouterLink class="button" to="/login">登录</RouterLink><RouterLink class="button primary" to="/register">注册体验</RouterLink></div>
  </header>

  <div class="shell-body" :class="{ 'public-shell': !showSidebar, 'homepage-shell': isHome }">
    <aside v-if="showSidebar" class="shell-sidebar">
      <nav v-if="inAdmin" class="admin-nav" aria-label="后台模块"><RouterLink v-for="item in adminLinks" :key="item.to" :to="item.to">{{ item.label }}</RouterLink></nav>
      <ConversationList v-else :key="session.epoch.value" />
      <div v-if="!inAdmin" class="sidebar-bottom">
        <p class="sidebar-balance"><span>可用积分</span><strong v-if="session.account.value">{{ session.account.value.available }}</strong><span v-else>积分读取中</span></p>
        <small v-if="session.account.value">冻结 {{ session.account.value.frozen }} · 已消费 {{ session.account.value.consumed }}</small>
        <RouterLink class="button" data-testid="header-recharge" to="/recharge"><AppIcon name="credits" />充值积分</RouterLink>
        <small>在线充值暂未开放</small>
      </div>
    </aside>
    <main id="main-content" tabindex="-1"><RouterView :key="session.epoch.value" /></main>
  </div>
  </div>
</template>

<style scoped>
.app-shell--auth { display:flex; flex-direction:column; min-height:100dvh; }
.app-shell--auth > .app-header { flex-shrink:0; }
.app-shell--auth > .shell-body { display:flex; flex:1; }
.app-shell--auth > .shell-body > main { display:flex; align-items:center; flex:1; min-width:0; padding:32px; }
@media(max-width:800px) { .app-shell--auth > .shell-body > main { align-items:flex-start; padding:28px 20px; } }
@media(max-width:420px) { .app-shell--auth > .shell-body > main { padding:20px 16px; } }
.app-shell--collection { height:100dvh; overflow:hidden; display:flex; flex-direction:column; }
.app-shell--collection > .app-header { flex-shrink:0; }
.app-shell--collection > .shell-body { flex:1; min-height:0; overflow:hidden; display:flex; flex-direction:column; }
.app-shell--collection > .shell-body > main { flex:1; min-height:0; overflow:hidden; display:flex; flex-direction:column; width:100%; }
.app-shell--admin { height:100dvh; overflow:hidden; display:flex; flex-direction:column; }
.app-shell--admin > .app-header { flex-shrink:0; }
.app-shell--admin > .shell-body { flex:1; min-height:0; overflow:hidden; grid-template-rows:minmax(0,1fr); }
.app-shell--admin .shell-sidebar { min-height:0; overflow-y:auto; overscroll-behavior-y:contain; }
.app-shell--admin > .shell-body > main { min-height:0; overflow-y:auto; overscroll-behavior-y:contain; }
.app-shell--admin-list > .shell-body > main { min-height:0; overflow:hidden; display:flex; flex-direction:column; }
.app-shell--admin .admin-nav { margin:0; }
@media(max-width:700px) {
  .app-shell--admin > .shell-body { display:flex; flex-direction:column; }
  .app-shell--admin .shell-sidebar { flex:none; display:block; padding:8px 12px; }
  .app-shell--admin .admin-nav { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:2px; }
  .app-shell--admin .admin-nav a { padding:6px 2px; min-height:44px; display:flex; align-items:center; justify-content:center; font-size:12px; white-space:nowrap; }
  .app-shell--admin > .shell-body > main { flex:1; padding:12px; }
}
.app-shell--workspace .sidebar-bottom { border-top:1px solid var(--color-border); padding-top:16px }
.app-shell--workspace .sidebar-balance { gap:6px }
.app-shell--workspace .sidebar-balance>strong { font-size:32px; letter-spacing:-.03em }
.app-shell--workspace .sidebar-bottom>.button { background:var(--color-panel); font-weight:600 }
@media(min-width:701px) {
  .app-shell--workspace { height:100dvh; display:flex; flex-direction:column; }
  .app-shell--workspace > .app-header { flex-shrink:0; }
  .app-shell--workspace > .shell-body { flex:1; min-height:0; grid-template-rows:minmax(0,1fr); }
  .app-shell--workspace .shell-sidebar { min-height:0; }
  .app-shell--workspace :deep(.conversation-nav) { flex:1; min-height:0; display:flex; flex-direction:column; }
  .app-shell--workspace :deep(.conversation-nav > .button),
  .app-shell--workspace .sidebar-bottom { flex-shrink:0; }
  .app-shell--workspace :deep(.desktop-history) { flex:1; min-height:0; overflow-y:auto; overscroll-behavior-y:contain; margin-top:20px; padding:0 8px 16px; margin-inline:-8px; }
  .app-shell--workspace :deep(.desktop-history > p:first-child) { margin-top:0; }
  .app-shell--workspace > .shell-body > main { min-height:0; overflow-y:auto; }
}
@media(min-width:901px) {
  .app-shell--workspace > .shell-body > main { overflow:hidden; }
}
@media(max-width:700px) {
  .app-shell--workspace .sidebar-bottom { margin-top:12px; padding-top:12px }
  .app-shell--workspace .sidebar-balance>strong { font-size:22px }
}
</style>
