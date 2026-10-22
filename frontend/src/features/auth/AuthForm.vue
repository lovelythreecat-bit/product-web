<script setup lang="ts">
import UiInput from '../../components/ui/UiInput.vue'
import UiButton from '../../components/ui/UiButton.vue'
import AuthShowcase from './AuthShowcase.vue'
import { onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { session } from './session'
import { ApiError } from '../../api/client'
import type { Schema } from '../../types/api'
const props = defineProps<{ register?: boolean }>()
const router = useRouter()
const account = ref(''), password = ref(''), confirmation = ref(''), error = ref('')
const accountError = ref(''), passwordError = ref(''), confirmationError = ref('')
let intent: Readonly<Schema<'RegisterRequest'>> | undefined
function edited() { intent = undefined; error.value = '' }
onBeforeUnmount(() => { password.value = ''; confirmation.value = ''; intent = undefined })
async function submit() {
  if (session.busy.value) return
  accountError.value = [...account.value].length < 3 || [...account.value].length > 64 ? '账号需要 3–64 个字符。' : ''
  passwordError.value = [...password.value].length < 10 || [...password.value].length > 128 ? '密码需要 10–128 个字符。' : ''
  confirmationError.value = props.register && password.value !== confirmation.value ? '两次密码不一致，请重新确认。' : ''
  if (accountError.value || passwordError.value || confirmationError.value) return
  error.value = ''
  if (props.register && !intent) intent = Object.freeze({ account: account.value, password: password.value, request_key: crypto.randomUUID() })
  try {
    if (await session.authenticate(intent ?? { account: account.value, password: password.value })) {
      password.value = ''; confirmation.value = ''; intent = undefined
      await router.replace('/workspace')
    }
  } catch (e) {
    // Never surface server validation details, request bodies or credentials.
    error.value = e instanceof ApiError && e.status === 0 ? props.register ? '网络连接失败，请重试。同一次注册重试会沿用原请求。' : '网络连接失败，请重试登录。' : props.register ? '注册未完成，请检查账号是否已使用，或稍后重试。' : '登录未完成，请检查账号和密码，或稍后重试。'
  }
}
</script>
<template>
  <section class="auth-layout" aria-labelledby="auth-title">
    <AuthShowcase />
    <div class="auth-form-panel">
    <div class="auth-card">
    <h1 id="auth-title">{{ register ? '注册体验' : '欢迎回来' }}</h1>
    <p class="auth-intro">使用账号密码，进入你的创作工作台。</p>
    <nav class="auth-tabs" aria-label="登录或注册"><RouterLink to="/login" :aria-current="!register ? 'page' : undefined" :class="{ active: !register }">登录</RouterLink><RouterLink to="/register" :aria-current="register ? 'page' : undefined" :class="{ active: register }">注册</RouterLink></nav>
    <slot name="notice" />
    <form class="form-stack" :aria-busy="session.busy.value" @submit.prevent="submit" novalidate>
      <div><div class="auth-field-label"><label for="auth-account">账号</label><small id="account-help">3–64 个字符</small></div><UiInput id="auth-account" v-model="account" :disabled="session.busy.value" autocomplete="username" placeholder="请输入账号" :aria-invalid="!!accountError" aria-describedby="account-help account-error" @input="edited" /><p id="account-error" class="field-error" role="alert">{{ accountError }}</p></div>
      <div><div class="auth-field-label"><label for="auth-password">密码</label><small id="password-help">10–128 个字符</small></div><UiInput id="auth-password" v-model="password" :disabled="session.busy.value" type="password" placeholder="请输入密码" :aria-invalid="!!passwordError" :autocomplete="register ? 'new-password' : 'current-password'" aria-describedby="password-help password-error" @input="edited" /><p id="password-error" class="field-error" role="alert">{{ passwordError }}</p></div>
      <div v-if="register"><label for="auth-confirmation">确认密码</label><UiInput id="auth-confirmation" v-model="confirmation" :disabled="session.busy.value" type="password" autocomplete="new-password" aria-describedby="confirmation-error" :aria-invalid="!!confirmationError" @input="confirmationError = ''; error = ''" /><p id="confirmation-error" class="field-error" role="alert">{{ confirmationError }}</p></div>
      <p v-if="error || session.error.value" class="field-error" role="alert">{{ error || session.error.value }}</p>
      <UiButton type="submit" class="button primary" :disabled="session.busy.value" :loading="session.busy.value">{{ session.busy.value ? '正在提交…' : register ? '创建账号' : '登录' }}</UiButton>
    </form>
    <div class="auth-footer"><p>{{ register ? '已有账号？' : '还没有账号？' }} <RouterLink :to="register ? '/login' : '/register'">{{ register ? '去登录' : '注册体验' }}</RouterLink></p></div>
    </div>
    </div>
  </section>
</template>
<style scoped>
.auth-layout { display:grid; grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr); width:100%; max-width:1180px; margin:0 auto; min-height:650px; border:1px solid var(--color-border); border-radius:var(--radius-panel); overflow:hidden; background:var(--color-panel); }
.auth-form-panel { display:flex; align-items:center; justify-content:center; min-width:0; padding:48px; }
.auth-card { width:100%; max-width:400px; }
.auth-card h1 { font-size:32px; line-height:1.35; margin:0 0 12px; letter-spacing:-.02em; }
.auth-intro { margin:0; font-size:14px; line-height:1.8; }
.auth-tabs { display:flex; gap:28px; border-bottom:1px solid var(--color-border); margin:28px 0; }
.auth-tabs a { display:flex; align-items:center; justify-content:center; min-width:64px; min-height:48px; padding:10px 8px; text-decoration:none; color:var(--color-muted); border-bottom:2px solid transparent; }
.auth-tabs a:hover { color:var(--color-primary); }
.auth-tabs .active { color:var(--color-primary); border-bottom-color:var(--color-primary); font-weight:600; }
.auth-card .form-stack { gap:22px; }
.auth-card label { font-size:14px; font-weight:500; }
.auth-field-label { display:flex; align-items:baseline; justify-content:space-between; flex-wrap:wrap; column-gap:12px; margin-bottom:8px; }
.auth-field-label label { margin:0; }
.auth-card small { font-size:12px; line-height:1.5; }
.auth-card :deep(.ui-input) { --el-input-height:48px; font-size:15px; }
.auth-card :deep(.el-input__wrapper) { min-height:48px; }
.auth-card :deep(.el-input__inner) { height:48px; caret-color:var(--color-primary); }
.auth-card .field-error:empty { display:none; }
.auth-card .field-error { margin:6px 0 0; font-size:13px; }
.auth-card .form-stack>.primary { width:100%; min-height:48px; margin-top:6px; font-size:15px; font-weight:600; }
.auth-footer { text-align:center; margin-top:28px; font-size:14px; }
.auth-footer p { margin:0; }
.auth-footer a { display:inline-flex; align-items:center; min-height:44px; color:var(--color-primary); font-weight:600; text-underline-offset:4px; }
@media(max-width:1000px) { .auth-form-panel { padding:36px 28px; } }
@media(max-width:800px) { .auth-layout { display:block; max-width:480px; min-height:0; } .auth-form-panel { padding:36px 28px; } .auth-card h1 { font-size:28px; } }
@media(max-width:420px) { .auth-layout { border:0; border-radius:0; background:transparent; } .auth-form-panel { padding:20px 8px; } .auth-tabs { margin-block:24px; } }
</style>
