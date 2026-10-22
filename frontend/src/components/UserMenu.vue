<script setup lang="ts">
import UiButton from './ui/UiButton.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { session } from '../features/auth/session'
import UserAvatar from './UserAvatar.vue'
const router = useRouter(), route = useRoute()
const root = ref<HTMLElement | null>(null), trigger = ref<HTMLButtonElement | null>(null), menu = ref<HTMLElement | null>(null)
const open = ref(false), logoutError = ref(''), menuId = useId()
const name = computed(() => session.profile.value?.nickname?.trim() || session.profile.value?.account || '用户')
function close(restoreFocus = false) { open.value = false; if (restoreFocus) trigger.value?.focus() }
async function show(last = false) {
  open.value = true; await nextTick()
  const items = menu.value?.querySelectorAll<HTMLElement>('[role="menuitem"]:not(:disabled)')
  if (items?.length) items[last ? items.length - 1 : 0]?.focus()
}
function toggle() { if (open.value) close(); else void show() }
function triggerKey(event: KeyboardEvent) {
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); void show(event.key === 'ArrowUp') }
  else if (event.key === 'Escape' && open.value) { event.preventDefault(); close(true) }
}
function menuKey(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); close(true); return }
  const keys = ['ArrowDown', 'ArrowUp', 'Home', 'End']
  if (!keys.includes(event.key)) return
  event.preventDefault()
  const items = Array.from(menu.value?.querySelectorAll<HTMLElement>('[role="menuitem"]:not(:disabled)') ?? [])
  if (!items.length) return
  const current = items.indexOf(document.activeElement as HTMLElement)
  const index = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : current < 0 ? (event.key === 'ArrowDown' ? 0 : items.length - 1) : (current + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length
  items[index]?.focus()
}
function outsideClick(event: MouseEvent) { if (event.target instanceof Node && !root.value?.contains(event.target)) close() }
function focusOut(event: FocusEvent) { if (!(event.relatedTarget instanceof Node) || !root.value?.contains(event.relatedTarget)) close() }
async function logout() {
  logoutError.value = ''
  const version = session.epoch.value
  try { if (await session.logout()) { close(); await router.replace('/login') } }
  catch { if (version === session.epoch.value) logoutError.value = '退出未完成，请重试。' }
}
watch(() => route?.fullPath, () => close())
watch(session.epoch, () => { close(); logoutError.value = '' })
onMounted(() => document.addEventListener('click', outsideClick))
onBeforeUnmount(() => document.removeEventListener('click', outsideClick))
</script>
<template>
  <div v-if="session.profile.value" ref="root" class="user-menu" @focusout="focusOut">
    <UiButton ref="trigger" type="button" class="user-menu-trigger" aria-haspopup="menu" :aria-expanded="open" :aria-controls="menuId" :aria-label="`${name}，用户菜单`" @click="toggle" @keydown="triggerKey">
      <UserAvatar :avatar="session.profile.value.avatar" :name="name" />
      <span class="user-menu-name" :title="name">{{ name }}</span>
      <svg class="user-menu-chevron" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m5 7.5 5 5 5-5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </UiButton>
    <div v-if="open" :id="menuId" ref="menu" class="user-menu-panel" role="menu" :aria-label="`${name}的账户操作`" @keydown="menuKey">
      <RouterLink role="menuitem" to="/workspace" target="_blank" rel="noopener noreferrer" @click="close()">进入工作台</RouterLink>
      <RouterLink role="menuitem" to="/account" @click="close()">个人中心</RouterLink>
      <UiButton type="button" role="menuitem" class="user-menu-logout" :disabled="session.busy.value" @click="logout">{{ session.busy.value ? '正在退出…' : '退出登录' }}</UiButton>
      <p v-if="logoutError" class="user-menu-error" role="alert">{{ logoutError }}</p>
    </div>
    <p v-if="logoutError && !open" class="user-menu-error user-menu-error--closed" role="alert">{{ logoutError }}</p>
  </div>
</template>
<style scoped>
.user-menu { position:relative; flex-shrink:0; color:var(--color-text,#322823); }
.user-menu-trigger { display:flex; align-items:center; gap:9px; min-height:48px; max-width:220px; padding:4px 8px; border:1px solid transparent; border-radius:var(--radius-control,8px); background:transparent; color:inherit; cursor:pointer; }
.user-menu-trigger:hover,.user-menu-trigger[aria-expanded="true"] { background:var(--color-selected,#f2dfcf); border-color:var(--color-border,#e7d9ca); }
.user-menu-name { min-width:0; max-width:128px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:14px; }
.user-menu-chevron { width:16px; height:16px; flex-shrink:0; }
.user-menu-panel { position:absolute; z-index:30; top:calc(100% + 8px); right:0; width:208px; max-width:calc(100vw - 32px); padding:8px; background:var(--color-panel,#fffdfa); border:1px solid var(--color-border,#e7d9ca); border-radius:12px; box-shadow:0 12px 30px #32282318; }
.user-menu-panel a,.user-menu-panel button { display:flex; align-items:center; width:100%; min-height:44px; padding:10px 12px; border:0; border-radius:6px; background:transparent; color:inherit; text-decoration:none; font:inherit; font-size:14px; text-align:left; }
.user-menu-panel a:hover,.user-menu-panel button:hover { background:var(--color-selected,#f2dfcf); }
.user-menu-panel .user-menu-logout { margin-top:6px; border-top:1px solid var(--color-border,#e7d9ca); border-radius:0 0 6px 6px; color:var(--color-danger,#a52b28); }
.user-menu-trigger:focus-visible,.user-menu-panel a:focus-visible,.user-menu-panel button:focus-visible { outline:2px solid var(--color-primary,#a94e32); outline-offset:2px; }
.user-menu-error { margin:6px 12px; color:var(--color-danger,#a52b28); font-size:13px; }
.user-menu-error--closed { position:absolute; z-index:30; top:calc(100% + 8px); right:0; width:208px; max-width:calc(100vw - 32px); margin:0; padding:10px 12px; border:1px solid var(--color-border,#e7d9ca); border-radius:8px; background:var(--color-panel,#fffdfa); box-shadow:0 8px 24px #32282318; }
@media(max-width:600px) { .user-menu-trigger { max-width:160px; padding:4px; gap:6px; } .user-menu-name { max-width:85px; } }
@media(max-width:700px) { .user-menu.shell-user-menu .user-menu-name { display:none; } .user-menu.shell-user-menu .user-menu-trigger { padding:4px; gap:4px; } }
</style>
